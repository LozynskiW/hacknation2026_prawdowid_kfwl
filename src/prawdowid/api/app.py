"""PRAWDOWID - backend: zapytanie -> agent Prawdowid w OpenCode V2 -> raport.

Uruchomienie:  uvicorn prawdowid.api.app:app --port 8000
               (backend sam uruchamia serwer OpenCode, patrz src/prawdowid/api/opencode.py)
Ustawienia:    src/prawdowid/api/settings.py (.env)

Kanały: strona WWW pod http://localhost:8000/ oraz bot Discorda (POST /api/v1/check).
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from datetime import date

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from prawdowid.api.opencode import AgentError, model_ref, server
from prawdowid.api.report import is_final, to_report
from prawdowid.api.settings import AGENT_TIMEOUT, AI_API_KEY, AI_MODEL, WEB_DIR
from prawdowid.api.sources import allowed_patterns
from prawdowid.api.web_view import to_template_context

log = logging.getLogger("prawdowid")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Serwer OpenCode startuje razem z backendem; gdy się nie uda, spróbujemy przy pierwszym pytaniu.
    if AI_API_KEY and AI_MODEL:
        try:
            await server.start()
        except (AgentError, OSError) as e:
            log.warning("OpenCode nie wystartował: %s", e)
    yield
    server.stop()


app = FastAPI(title="PRAWDOWID", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")


class CheckIn(BaseModel):
    # channel tylko informacyjnie (logi) - logika i wynik są takie same dla każdego kanału.
    channel: str = "WEB"
    text: str | None = None
    url: str | None = None


def user_message(body: CheckIn) -> str:
    # Data, bo model nie wie, jaki jest dziś dzień (agent ma nie opierać się na wiedzy z treningu).
    parts = [f"Dzisiejsza data: {date.today().isoformat()}"]
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
        return failure("Brak konfiguracji modelu (AI_API_KEY / AI_MODEL).")
    try:
        ask = server.ask(user_message(body), timeout=AGENT_TIMEOUT, is_final=is_final)
        answer = await asyncio.wait_for(ask, AGENT_TIMEOUT + 30)
    except (TimeoutError, httpx.TimeoutException):
        return failure("Sprawdzanie trwało zbyt długo. Spróbuj ponownie.")
    except httpx.HTTPStatusError as e:
        log.warning("OpenCode: HTTP %s %s", e.response.status_code, e.response.text[:500])
        return failure(f"Agent zwrócił błąd {e.response.status_code}.")
    except AgentError as e:
        log.warning("OpenCode: %s", str(e)[:500])
        if e.kind == "provider.quota":
            return failure("Wyczerpał się limit zapytań do modelu. Spróbuj ponownie później.")
        if e.kind == "provider.auth":
            return failure("Dostawca modelu odrzucił klucz API. Sprawdź AI_API_KEY i AI_PROVIDER w .env.")
        return failure("Nie udało się wykonać sprawdzenia. Spróbuj ponownie.")
    except (httpx.HTTPError, KeyError, OSError) as e:
        return failure(f"Nie udało się wykonać sprawdzenia ({type(e).__name__}).")
    # Agent zwrócił JSON w uzgodnionym formacie → karty; inaczej → zwykły tekst.
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
    running = server.process is not None and server.process.poll() is None
    return {"status": "ok", "agentRunning": running, "model": model_ref(), "keySet": bool(AI_API_KEY),
            "allowedSources": len(allowed_patterns())}


@app.post("/api/v1/check")
async def check(body: CheckIn):
    result = await run_check(body)
    if result.get("status") == "TECHNICAL_FAILURE" and "checkId" not in result:
        return JSONResponse(status_code=503, content=result)
    return result
