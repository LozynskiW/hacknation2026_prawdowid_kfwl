"""PRAWDOWID - backend: zapytanie + agent -> dostawca AI -> raport.

Uruchomienie:  uvicorn prawdowid.api.app:app --port 8000
Ustawienia:    src/prawdowid/api/settings.py (.env)

Kanały: strona WWW pod http://localhost:8000/ oraz bot Discorda (POST /api/v1/check).
"""

import re

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from prawdowid.api.agent import agent_files, system_prompt
from prawdowid.api.providers import ask_ai
from prawdowid.api.report import to_report
from prawdowid.api.settings import AGENT_DIR, AI_API_KEY, AI_MODEL, AI_PROVIDER, WEB_DIR
from prawdowid.api.web_view import to_template_context

app = FastAPI(title="PRAWDOWID")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")


class CheckIn(BaseModel):
    # channel tylko informacyjnie (logi) - logika i wynik są takie same dla każdego kanału.
    channel: str = "WEB"
    text: str | None = None
    url: str | None = None


def user_message(body: CheckIn) -> str:
    parts = []
    if body.text:
        parts.append(f"Wiadomość od użytkownika:\n{body.text}")
    if body.url:
        parts.append(f"Link od użytkownika: {body.url}")
    return "\n\n".join(parts)


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
        answer = await ask_ai(system_prompt(), user_message(body))
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
            "agentFiles": [str(p.relative_to(AGENT_DIR)) for p in agent_files()]}


@app.post("/api/v1/check")
async def check(body: CheckIn):
    result = await run_check(body)
    if result.get("status") == "TECHNICAL_FAILURE" and "checkId" not in result:
        return JSONResponse(status_code=503, content=result)
    return result
