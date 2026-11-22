"""Adapter: wynik z run_check() -> kontekst szablonu templates/result.html.

Szablon przyjmuje pola PresentationModel (summary, claims z label / sources / warnings / unknowns).
Gdy zmieni się format odpowiedzi skilla, wystarczy poprawić ten plik - szablon i front zostają bez zmian.
"""

LABELS = {
    "CONFIRMED": "Potwierdzone",
    "FALSE": "Fałszywe",
    "MISLEADING": "Wprowadza w błąd",
    "INSUFFICIENT_EVIDENCE": "Brak wystarczających dowodów",
    "NOT_CHECKABLE": "Nie podlega weryfikacji (opinia lub prognoza)",
}

# Do podsumowania: "Sprawdzono 2 twierdzenia: 1 fałszywe, 1 bez wystarczających dowodów."
SUMMARY_WORDS = {
    "CONFIRMED": "potwierdzone",
    "FALSE": "fałszywe",
    "MISLEADING": "wprowadzające w błąd",
    "INSUFFICIENT_EVIDENCE": "bez wystarczających dowodów",
    "NOT_CHECKABLE": "niepodlegające weryfikacji",
}

DEFAULT_MESSAGES = {
    "NEEDS_CLARIFICATION": "Napisz dokładniej, którą informację mamy sprawdzić, albo wklej link do artykułu.",
    "OUT_OF_SCOPE": "Tej informacji nie sprawdzamy - jest poza tematami, którymi się zajmujemy.",
    "RATE_LIMITED": "Za dużo zapytań w krótkim czasie. Spróbuj ponownie za minutę.",
    "TECHNICAL_FAILURE": "Spróbuj ponownie za chwilę.",
}


def _claims_word(n: int) -> str:
    if n == 1:
        return "twierdzenie"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "twierdzenia"
    return "twierdzeń"


def _percent(confidence) -> str:
    """0.98 -> "98%". Brak lub zła wartość -> pusty tekst (nie pokazujemy)."""
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return ""
    if value <= 1:
        value *= 100
    return f"{round(min(max(value, 0), 100))}%"


def _verdict(claim: dict) -> str:
    outcome = claim.get("outcome") or {}
    if outcome.get("kind") == "NOT_CHECKABLE":
        return "NOT_CHECKABLE"
    return outcome.get("verdict") or "INSUFFICIENT_EVIDENCE"


def to_template_context(result: dict, question: str) -> dict:
    """Zamienia raport (format z prawdowid.api.report.to_report), {"answer": ...} lub awarię na kontekst szablonu."""
    if "answer" in result:
        # Model nie oddał JSON-a w uzgodnionym formacie - pokazujemy jego tekst.
        return {"status": "TEXT", "question": question, "answer": result["answer"]}

    status = result.get("status") or "TECHNICAL_FAILURE"
    if status != "COMPLETED":
        message = result.get("statusMessage") or DEFAULT_MESSAGES.get(status, DEFAULT_MESSAGES["TECHNICAL_FAILURE"])
        return {"status": status, "question": question, "message": message}

    evidence = {e["evidenceId"]: e for e in result.get("evidence") or []}
    claims, counts = [], {}
    for c in result.get("claims") or []:
        verdict = _verdict(c)
        counts[verdict] = counts.get(verdict, 0) + 1
        sources = []
        for eid in c.get("evidenceIds") or []:
            e = evidence.get(eid)
            if not e:
                continue
            src = e.get("source") or {}
            sources.append({
                "title": src.get("title") or src.get("url") or "",
                "publisher": src.get("publisher") or "",
                "url": src.get("url") or "",
                "published_at": src.get("publishedAt") or "",
                "quote": e.get("quote") or "",
            })
        claims.append({
            "text": c.get("text", ""),
            "label": LABELS.get(verdict, verdict),
            "short_answer": c.get("shortAnswer") or "",
            "confidence": _percent(c.get("confidence")),
            "relevance": c.get("relevance", 3),
            "explanation": c.get("explanation", ""),
            "sources": sources,
            "warnings": [w.get("message", "") for w in c.get("warnings") or [] if w.get("message")],
            "unknowns": c.get("unknowns") or [],
        })

    total = len(claims)
    parts = [f"{n} {SUMMARY_WORDS.get(v, v)}" for v, n in counts.items()]
    tally = f"Sprawdzono {total} {_claims_word(total)}: {', '.join(parts)}." if total else ""
    # Podsumowanie skilla, a gdy go nie ma (albo zostało odrzucone) - zliczenie werdyktów.
    view = {"summary": result.get("summary") or tally, "tally": tally, "claims": claims,
            "overall_verdict": LABELS.get(result.get("overallVerdict") or "", result.get("overallVerdict")),
            "verdict_counts": result.get("verdictCounts") or {}}
    return {"status": "OK", "question": question, "original_message": result.get("originalMessage"),
            "view": view, "handoff": (result.get("handoff") or {}).get("status") == "RECOMMENDED"}
