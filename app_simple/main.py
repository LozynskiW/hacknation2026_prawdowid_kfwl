"""PRAWDOWID – prosta aplikacja: zapytanie + skill → dostawca AI → odpowiedź.

Uruchomienie:  uvicorn app_simple.main:app --port 8000

.env:
  AI_PROVIDER=anthropic          # albo: openai (każde API zgodne z OpenAI)
  AI_API_KEY=...
  AI_MODEL=claude-sonnet-5-5
  AI_BASE_URL=                   # opcjonalnie, np. http://localhost:11434/v1 dla openai
  SKILL_DIR=skills/prawdowid     # folder ze skillem (SKILL.md + ewentualne inne pliki .md)

Kanały: strona WWW pod http://localhost:8000/ oraz bot Discorda – oba wołają POST /api/v1/check.
"""

import json
import os
import re
import unicodedata
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import asyncio

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app_simple.web_view import to_template_context

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "")
SKILL_DIR = Path(os.getenv("SKILL_DIR", "skills/prawdowid"))
WHITELIST_FILE = Path(os.getenv("WHITELIST_FILE", "config/whitelist.txt"))
FORMAT_FILE = Path(__file__).with_name("format_odpowiedzi.md")

# Front WWW (szablony + statyczne pliki) z modułu presentation.
WEB_DIR = Path(__file__).resolve().parents[1] / "src" / "prawdowid" / "presentation"

app = FastAPI(title="PRAWDOWID")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")


class CheckIn(BaseModel):
    # channel tylko informacyjnie (logi) – logika i wynik są takie same dla każdego kanału.
    channel: str = "WEB"
    text: str | None = None
    url: str | None = None


def load_skill() -> str:
    """SKILL.md jako pierwszy, potem pozostałe pliki .md z folderu skilla, na końcu format odpowiedzi."""
    files = sorted(SKILL_DIR.rglob("*.md"), key=lambda p: (p.name != "SKILL.md", str(p)))
    skill = "\n\n".join(f"<!-- {p.relative_to(SKILL_DIR)} -->\n{p.read_text(encoding='utf-8')}" for p in files)
    return f"{skill}\n\n{FORMAT_FILE.read_text(encoding='utf-8')}"


def whitelist_hosts() -> set[str]:
    if not WHITELIST_FILE.exists():
        return set()
    return {urlsplit(line.strip()).hostname or "" for line in WHITELIST_FILE.read_text().splitlines() if line.strip()}


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
    if not isinstance(data, dict) or not ("claims" in data or "error" in data):
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
    allowed = whitelist_hosts()
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
            if allowed and host not in allowed:  # źródło spoza whitelisty - nie pokazujemy go jako dowodu
                warnings.append({"code": "SOURCE_REMOVED", "message": f"Pominięto źródło spoza listy dozwolonych ({host})."})
                continue
            eid = f"e{len(report['evidence']) + 1}"
            ids.append(eid)
            report["evidence"].append({
                "evidenceId": eid, "type": "QUOTE", "quote": s.get("exact_quote"),
                "source": {"title": s.get("title") or host, "publisher": s.get("publisher") or host,
                           "url": s.get("url"), "publishedAt": s.get("publication_date") or None},
            })

        explanation = c.get("detailed_justification_pl") or ""
        short_answer = c.get("summary_response_pl") or ""
        confidence = c.get("confidence_score")
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


def user_message(body: CheckIn) -> str:
    parts = []
    if body.text:
        parts.append(f"Wiadomość od użytkownika:\n{body.text}")
    if body.url:
        parts.append(f"Link od użytkownika: {body.url}")
    return "\n\n".join(parts)


async def ask_ai(system: str, message: str) -> str:
    """Wysyła skill + wiadomość do dostawcy AI. Ponawia do 3 razy przy 429/500/503."""
    for attempt in range(3):
        try:
            return await _ask_ai_once(system, message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 503) and attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))  # 2 s, potem 4 s
                continue
            print("Błąd dostawcy AI:", e.response.status_code, e.response.text[:500])
            raise


async def _ask_ai_once(system: str, message: str) -> str:
    base = (AI_BASE_URL or "").rstrip("/")
    async with httpx.AsyncClient(timeout=300) as client:
        if AI_PROVIDER == "gemini":
            r = await client.post(
                f"{base or 'https://generativelanguage.googleapis.com/v1beta'}/models/{AI_MODEL}:generateContent",
                headers={"x-goog-api-key": AI_API_KEY},
                json={"systemInstruction": {"parts": [{"text": system}]},
                      "contents": [{"role": "user", "parts": [{"text": message}]}]},
            )
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))

        if AI_PROVIDER == "anthropic":
            r = await client.post(
                f"{base or 'https://api.anthropic.com'}/v1/messages",
                headers={"x-api-key": AI_API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": AI_MODEL, "max_tokens": 4096, "system": system,
                      "messages": [{"role": "user", "content": message}]},
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")

        if AI_PROVIDER == "openai":
            r = await client.post(
                f"{base or 'https://api.openai.com/v1'}/chat/completions",
                headers={"Authorization": f"Bearer {AI_API_KEY}"},
                json={"model": AI_MODEL, "messages": [{"role": "system", "content": system},
                                                      {"role": "user", "content": message}]},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""

        raise ValueError(f"Nieznany AI_PROVIDER: {AI_PROVIDER} (dozwolone: gemini, anthropic, openai)")


def failure(message: str) -> dict:
    # Awaria to nie wynik sprawdzenia – kanały pokazują ją jako błąd techniczny.
    return {"status": "TECHNICAL_FAILURE", "statusMessage": message}


async def run_check(body: CheckIn) -> dict:
    """Wspólna logika dla API (bot) i strony WWW. Zwraca raport, {"answer": tekst} albo awarię."""
    if not (body.text or body.url):
        return failure("Brak treści do sprawdzenia.")
    if not AI_API_KEY or not AI_MODEL:
        return failure("Brak konfiguracji dostawcy AI (AI_API_KEY / AI_MODEL).")
    try:
        answer = await ask_ai(load_skill(), user_message(body))
    except httpx.TimeoutException:
        return failure("Dostawca AI nie odpowiedział na czas. Spróbuj ponownie.")
    except httpx.HTTPStatusError as e:
        print(e.response.text)
        return failure(f"Dostawca AI zwrócił błąd {e.response.status_code}.")
    except (httpx.HTTPError, KeyError, IndexError, OSError) as e:
        return failure(f"Nie udało się wykonać sprawdzenia ({type(e).__name__}).")
    # Model zwrócił JSON w uzgodnionym formacie → karty; inaczej → zwykły tekst.
    return to_report(answer) or {"answer": answer}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Strona WWW: obserwujące oko i pole pytania."""
    return templates.TemplateResponse(request, "index.html")


@app.post("/wynik", response_class=HTMLResponse)
async def web_check(request: Request, text: str = Form("")):
    """Formularz ze strony (HTMX): ta sama logika co /api/v1/check, wynik jako fragment HTML."""
    text = text.strip()
    # Sam link w polu traktujemy jak link do sprawdzenia, resztę jak tekst.
    is_url = re.fullmatch(r"https?://\S+", text) is not None
    body = CheckIn(channel="WEB", text=None if is_url else text or None, url=text if is_url else None)
    report = await run_check(body)
    return templates.TemplateResponse(request, "result.html", to_template_context(report, question=text))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "provider": AI_PROVIDER, "model": AI_MODEL, "keySet": bool(AI_API_KEY),
            "skillFiles": [str(p.relative_to(SKILL_DIR)) for p in SKILL_DIR.rglob("*.md")] if SKILL_DIR.exists() else []}


@app.post("/api/v1/check")
async def check(body: CheckIn):
    result = await run_check(body)
    if result.get("status") == "TECHNICAL_FAILURE" and "checkId" not in result:
        return JSONResponse(status_code=503, content=result)
    return result
