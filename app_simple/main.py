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
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import asyncio

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "")
SKILL_DIR = Path(os.getenv("SKILL_DIR", "skills/prawdowid"))
WHITELIST_FILE = Path(os.getenv("WHITELIST_FILE", "config/whitelist.txt"))
FORMAT_FILE = Path(__file__).with_name("format_odpowiedzi.md")

app = FastAPI(title="PRAWDOWID")


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


def to_report(answer: str) -> dict | None:
    """JSON od modelu → format, który bot wyświetla jako karty. None = to nie był poprawny JSON."""
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "status" not in data:
        return None

    report = {"checkId": f"chk_{uuid.uuid4().hex[:12]}", "status": data["status"],
              "statusMessage": data.get("statusMessage"), "claims": [], "evidence": [],
              "handoff": {"status": "RECOMMENDED" if data.get("handoff") else "NONE"}}
    allowed = whitelist_hosts()
    for i, c in enumerate((data.get("claims") or [])[:5], start=1):
        verdict = c.get("verdict", "INSUFFICIENT_EVIDENCE")
        ids, warnings = [], [{"code": "NOTE", "message": w} for w in c.get("warnings", []) if w]
        for s in c.get("sources") or []:
            host = urlsplit(str(s.get("url", ""))).hostname or ""
            if allowed and host not in allowed:  # źródło spoza whitelisty – nie pokazujemy go jako dowodu
                warnings.append({"code": "SOURCE_REMOVED", "message": f"Pominięto źródło spoza listy dozwolonych ({host})."})
                continue
            eid = f"e{len(report['evidence']) + 1}"
            ids.append(eid)
            report["evidence"].append({
                "evidenceId": eid, "type": "QUOTE", "quote": s.get("quote"),
                "source": {"title": s.get("title") or host, "publisher": s.get("publisher") or host,
                           "url": s.get("url"), "publishedAt": s.get("date")},
            })
        if verdict in ("CONFIRMED", "FALSE", "MISLEADING") and not ids:
            verdict = "INSUFFICIENT_EVIDENCE"  # werdykt bez źródła = wstrzymanie się
            warnings.append({"code": "NO_SOURCE", "message": "Brak źródła z listy dozwolonych – wstrzymujemy się od oceny."})
        unknowns = c.get("unknowns") or ([] if verdict != "INSUFFICIENT_EVIDENCE" else ["Nie znaleziono źródła rozstrzygającego."])
        report["claims"].append({
            "claimId": f"c{i}", "text": c.get("text", ""),
            "outcome": {"kind": "NOT_CHECKABLE"} if verdict == "NOT_CHECKABLE" else {"kind": "VERDICT", "verdict": verdict},
            "explanation": c.get("explanation", ""), "evidenceIds": ids, "warnings": warnings, "unknowns": unknowns,
            "strength": {"level": c.get("strength", "LOW"),
                         "factors": {"independentSources": len({report["evidence"][int(e[1:]) - 1]["source"]["publisher"] for e in ids})}}
            if verdict in ("CONFIRMED", "FALSE", "MISLEADING") else None,
        })
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


def error(message: str) -> JSONResponse:
    # Awaria to nie wynik sprawdzenia – bot pokaże ją jako błąd techniczny.
    return JSONResponse(status_code=503, content={"status": "TECHNICAL_FAILURE", "statusMessage": message})


@app.get("/")
async def index() -> FileResponse:
    """Strona WWW – woła ten sam /api/v1/check co bot."""
    return FileResponse(Path(__file__).with_name("index.html"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "provider": AI_PROVIDER, "model": AI_MODEL, "keySet": bool(AI_API_KEY),
            "skillFiles": [str(p.relative_to(SKILL_DIR)) for p in SKILL_DIR.rglob("*.md")] if SKILL_DIR.exists() else []}


@app.post("/api/v1/check")
async def check(body: CheckIn):
    if not (body.text or body.url):
        return error("Brak treści do sprawdzenia.")
    if not AI_API_KEY or not AI_MODEL:
        return error("Brak konfiguracji dostawcy AI (AI_API_KEY / AI_MODEL).")
    try:
        answer = await ask_ai(load_skill(), user_message(body))
    except httpx.TimeoutException:
        return error("Dostawca AI nie odpowiedział na czas. Spróbuj ponownie.")
    except httpx.HTTPStatusError as e:
        print(e.response.text)
        return error(f"Dostawca AI zwrócił błąd {e.response.status_code}.")
    except (httpx.HTTPError, KeyError, IndexError, OSError) as e:
        return error(f"Nie udało się wykonać sprawdzenia ({type(e).__name__}).")
    # Model zwrócił JSON w uzgodnionym formacie → karty w bocie; inaczej → zwykły tekst.
    return to_report(answer) or {"answer": answer}
