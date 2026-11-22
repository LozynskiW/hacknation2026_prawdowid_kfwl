"""JSON od agenta -> raport, z którego korzystają strona WWW i bot Discorda.

Tu działa filtr listy dozwolonych źródeł (te same wzorce, którymi OpenCode ogranicza agenta): źródło spoza listy nie jest pokazywane jako dowód,
a werdykt bez żadnego dozwolonego źródła zamieniamy na brak wystarczających dowodów.
"""

import json
import re
import unicodedata
import uuid
from urllib.parse import urlsplit

from prawdowid.api.sources import is_allowed


# Werdykty skilla (po polsku) -> kody raportu, z którego korzystają strona i bot.
SKILL_VERDICTS = {
    "POTWIERDZONE": "CONFIRMED",
    "FALSZYWE": "FALSE",
    "WPROWADZAJACE_W_BLAD": "MISLEADING",
    "BRAK_WYSTARCZAJACYCH_DOWODOW": "INSUFFICIENT_EVIDENCE",
    "NIE_PODLEGA_WERYFIKACJI": "NOT_CHECKABLE",
}
NO_SOURCE_TEXT = ("Nie znaleźliśmy potwierdzenia w źródłach z listy dozwolonych, "
                  "dlatego nie oceniamy tego twierdzenia.")


def _verdict_code(value) -> str:
    """"Fałszywe", "FAŁSZYWE", "falszywe" -> "FALSE". Nieznana wartość = brak wystarczających dowodów."""
    key = unicodedata.normalize("NFKD", str(value or "")).replace("ł", "l").replace("Ł", "L")
    key = "".join(ch for ch in key if not unicodedata.combining(ch))
    key = re.sub(r"[^A-Z]+", "_", key.upper()).strip("_")
    return SKILL_VERDICTS.get(key) or (key if key in SKILL_VERDICTS.values() else "INSUFFICIENT_EVIDENCE")


def _strength(confidence) -> str:
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return "LOW"
    return "HIGH" if c >= 0.8 else "MEDIUM" if c >= 0.5 else "LOW"


def _date(value) -> str | None:
    """Data publikacji tylko w postaci RRRR-MM-DD (model potrafi wpisać "brak", "listopad 2026" itp.)."""
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(value or "").strip())
    return m.group(0) if m else None


def _confidence(value) -> float | None:
    """Pewność jako liczba 0-1 ("0.9", 0.9, "90%", 90 -> 0.9). Inna wartość -> brak pewności."""
    try:
        c = float(str(value).strip().rstrip("%").replace(",", "."))
    except (TypeError, ValueError):
        return None
    c = c / 100 if c > 1 else c
    return c if 0 <= c <= 1 else None


def _error_message(error) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error.get("reason") or error.get("code") or "Błąd skilla.")
    return str(error)


def to_report(answer: str) -> dict | None:
    """JSON ze skilla -> raport dla strony i bota. None = to nie był poprawny JSON.

    Format skilla: original_message, overall_verdict, confidence_score, executive_summary,
    claims[claim_id, evaluated_claim, verdict, confidence_score, summary_response_pl,
    detailed_justification_pl, refusal_to_judge, sources_used[...]], error.
    """
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    data = {k.strip().rstrip(":"): v for k, v in data.items()}  # "claims:" -> "claims"
    if str(data.get("status", "")).upper() == "ODRZUCONE":
        # Skill input-formatter-validator odrzucił wiadomość (poza zakresem, porada, injection...).
        return {"checkId": f"chk_{uuid.uuid4().hex[:12]}", "status": "OUT_OF_SCOPE",
                "statusMessage": data.get("rejection_reason_pl") or None}
    if not ("claims" in data or "error" in data):
        return None

    check_id = f"chk_{uuid.uuid4().hex[:12]}"
    if data.get("error"):
        return {"checkId": check_id, "status": "TECHNICAL_FAILURE", "statusMessage": _error_message(data["error"])}

    claims_in = [c for c in data.get("claims") or [] if isinstance(c, dict)][:5]
    if not claims_in:
        # Skill nie wyodrębnił żadnego twierdzenia - prosimy o doprecyzowanie.
        return {"checkId": check_id, "status": "NEEDS_CLARIFICATION",
                "statusMessage": data.get("executive_summary") or None}

    report = {"checkId": check_id, "status": "COMPLETED", "statusMessage": None,
              "summary": data.get("executive_summary") or "", "claims": [], "evidence": [],
              "handoff": {"status": "NONE"}}
    downgraded = False
    for i, c in enumerate(claims_in, start=1):
        verdict = _verdict_code(c.get("verdict"))
        refusal = c.get("refusal_to_judge") or {}
        ids, warnings = [], []
        if refusal.get("is_refused") and refusal.get("reason"):
            warnings.append({"code": "REFUSED", "message": f"Nie oceniamy: {refusal['reason']}"})
        for s in c.get("sources_used") or []:
            if not isinstance(s, dict):
                continue
            host = urlsplit(str(s.get("url", ""))).hostname or ""
            if not is_allowed(str(s.get("url", ""))):  # źródło spoza listy - nie pokazujemy go jako dowodu
                warnings.append({"code": "SOURCE_REMOVED", "message": f"Pominięto źródło spoza listy dozwolonych ({host})."})
                continue
            eid = f"e{len(report['evidence']) + 1}"
            ids.append(eid)
            report["evidence"].append({
                "evidenceId": eid, "type": "QUOTE", "quote": s.get("exact_quote"),
                "source": {"title": s.get("title") or host, "publisher": s.get("publisher") or host,
                           "url": s.get("url"), "publishedAt": _date(s.get("publication_date"))},
            })

        explanation = c.get("detailed_justification_pl") or ""
        short_answer = c.get("summary_response_pl") or ""
        confidence = _confidence(c.get("confidence_score"))
        if verdict in ("CONFIRMED", "FALSE", "MISLEADING") and not ids:
            # Werdykt bez źródła = wstrzymanie się. Tekstu modelu nie pokazujemy jako faktu.
            verdict, explanation, short_answer, confidence, downgraded = (
                "INSUFFICIENT_EVIDENCE", NO_SOURCE_TEXT, "", None, True)
            warnings.append({"code": "NO_SOURCE", "message": "Brak źródła z listy dozwolonych - wstrzymujemy się od oceny."})
        unknowns = ["Nie znaleziono źródła rozstrzygającego."] if verdict == "INSUFFICIENT_EVIDENCE" and not ids else []
        report["claims"].append({
            "claimId": c.get("claim_id") or f"c{i}", "text": c.get("evaluated_claim", ""),
            "outcome": {"kind": "NOT_CHECKABLE"} if verdict == "NOT_CHECKABLE" else {"kind": "VERDICT", "verdict": verdict},
            "shortAnswer": short_answer, "explanation": explanation, "confidence": confidence,
            "evidenceIds": ids, "warnings": warnings, "unknowns": unknowns,
            "strength": {"level": _strength(confidence),
                         "factors": {"independentSources": len({report["evidence"][int(e[1:]) - 1]["source"]["publisher"] for e in ids})}}
            if verdict in ("CONFIRMED", "FALSE", "MISLEADING") else None,
        })
    if downgraded:
        report["summary"] = ""  # podsumowanie skilla opisuje werdykty, których nie potwierdziliśmy
    return report


def is_final(answer: str) -> bool:
    """Czy odpowiedź agenta to gotowy wynik: raport z treścią twierdzeń, odrzucenie, błąd albo prośba
    o doprecyzowanie. Wynik pośredni skilla albo raport z pustymi twierdzeniami -> ponaglamy agenta."""
    report = to_report(answer)
    if report is None:
        return False
    return report["status"] != "COMPLETED" or all(c["text"].strip() for c in report["claims"])

