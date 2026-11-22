"""PRAWDOWID - backend: zapytanie -> agent Prawdowid w OpenCode V2 -> raport.

Uruchomienie:  uvicorn prawdowid.api.app:app --port 8000
               (backend sam uruchamia serwer OpenCode, patrz src/prawdowid/api/opencode.py)
Ustawienia:    src/prawdowid/api/settings.py (.env)

Kanały: strona WWW pod http://localhost:8000/ oraz bot Discorda (POST /api/v1/check).
Log sprawdzeń (SQLite): src/prawdowid/api/checklog.py, podgląd GET /api/v1/log.
"""

import asyncio
import logging
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date

import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field

from prawdowid.api import checklog
from prawdowid.api.limits import RateLimiter, rate_limited_message, validate
from prawdowid.api.opencode import AgentError, model_ref, server
from prawdowid.api.pii import mask
from prawdowid.api.report import is_final, to_report
from prawdowid.api.settings import (
    ADMIN_TOKEN,
    AGENT_TIMEOUT,
    AI_API_KEY,
    AI_MODEL,
    LOG_RETENTION_DAYS,
    MAX_TEXT_CHARS,
    WEB_DIR,
)
from prawdowid.api.sources import allowed_patterns
from prawdowid.api.web_view import to_template_context

log = logging.getLogger("prawdowid")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # bez linii przy każdym odpytaniu agenta (co 1 s)

# Typowe zwroty prób obejścia zasad (prompt injection) w treści od użytkownika - tylko do logu (FR-51).
# Samą obronę robi agent (treść = dane, nie polecenia) i skill walidacji, który takie wiadomości odrzuca.
INJECTION_RE = re.compile(
    r"zignoruj\w*\s+(?:\w+\s+){0,3}(?:instrukcj|polece|zasad|regu)|ignore\s+(?:\w+\s+){0,3}(?:instructions|rules|prompt)"
    r"|system\s*prompt|prompt\s*systemow|jeste[śs]\s+teraz|you\s+are\s+now|developer\s+mode|jailbreak",
    re.IGNORECASE,
)


limiter = RateLimiter()


def _rate_limit(request: Request, body: "CheckIn") -> dict | None:
    """FR-53: po przekroczeniu limitu komunikat (status RATE_LIMITED), a nie błąd usługi.
    Klucz: pseudonim z Discorda, a dla strony adres IP (tylko w pamięci, przez minutę)."""
    key = f"user:{body.user_ref}" if body.user_ref else f"ip:{request.client.host if request.client else '?'}"
    retry_after = limiter.hit(key)
    if retry_after is None:
        return None
    log.warning("limit zapytań: kanał=%s, ponowna próba za %s s", body.channel, retry_after)
    return {"status": "RATE_LIMITED", "statusMessage": rate_limited_message(retry_after), "retryAfter": retry_after}


async def _purge_loop() -> None:
    """Retencja logu (FR-81): co godzinę usuwamy wpisy starsze niż LOG_RETENTION_DAYS."""
    while True:
        removed = await asyncio.to_thread(checklog.purge)
        if removed:
            log.info("log: usunięto %s wpisów starszych niż %s dni", removed, LOG_RETENTION_DAYS)
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_: FastAPI):
    checklog.init()
    purger = asyncio.create_task(_purge_loop())
    # Serwer OpenCode startuje razem z backendem; gdy się nie uda, spróbujemy przy pierwszym pytaniu.
    if AI_API_KEY and AI_MODEL:
        try:
            await server.start()
        except (AgentError, OSError) as e:
            log.warning("OpenCode nie wystartował: %s", e)
    yield
    purger.cancel()
    server.stop()


app = FastAPI(title="PRAWDOWID", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")
# Wersja CSS/JS w adresie (?v=...), żeby przeglądarka po zmianie pobrała nowe pliki, a nie starą kopię.
templates.env.globals["static_version"] = max(
    int(p.stat().st_mtime) for p in (WEB_DIR / "static").rglob("*") if p.is_file()
)


class CheckIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    # channel tylko informacyjnie (logi) - logika i wynik są takie same dla każdego kanału.
    channel: str = "WEB"
    text: str | None = None
    url: str | None = None
    # Discord: pseudonim użytkownika (HMAC) i identyfikator rozmowy. Strona WWW nie wysyła nic.
    user_ref: str | None = Field(default=None, alias="userRef")
    conversation_id: str | None = Field(default=None, alias="conversationId")


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
    """Wspólna logika dla API (bot) i strony WWW: maskowanie danych osobowych, agent, zapis w logu.
    Zwraca raport, {"answer": tekst} albo awarię - zawsze z checkId (do usunięcia wpisu z logu)."""
    started = time.monotonic()
    text, pii_text = mask(body.text)
    url, pii_url = mask(body.url)
    masked = body.model_copy(update={"text": text, "url": url})  # do modelu i logu trafia tylko to
    stats: dict = {}
    problem = validate(body.text, body.url)  # FR-52: nieprawidłowe wejście nie trafia do agenta
    result = ({"status": "NEEDS_CLARIFICATION", "statusMessage": problem} if problem
              else await _ask_agent(masked, stats))
    result.setdefault("checkId", f"chk_{uuid.uuid4().hex[:12]}")
    entry = _log_entry(masked, result, stats, sorted(set(pii_text + pii_url)), int((time.monotonic() - started) * 1000))
    try:
        await asyncio.to_thread(checklog.record, entry)
    except Exception as e:  # noqa: BLE001 - awaria logu nie może zepsuć odpowiedzi
        log.warning("log: nie zapisano sprawdzenia: %s", e)
    # Konsola: jedna linia na sprawdzenie, bez treści pytania.
    log.info("check %s channel=%s status=%s verdicts=%s latency_ms=%s cost_usd=%s fetches=%s/%s injection=%s pii=%s",
             entry["check_id"], entry["channel"], entry["status"], ",".join(entry["verdicts"]) or "-",
             entry["latency_ms"], entry["cost_usd"], entry["fetch_errors"], entry["fetches"],
             entry["injection"], entry["pii_masked"] or "-")
    if entry["injection"]:
        log.warning("check %s: wykryto próbę prompt injection (%s)", entry["check_id"], entry["rejection"] or "wzorzec w treści")
    return result


def _log_entry(body: CheckIn, result: dict, stats: dict, pii: list[str], latency_ms: int) -> dict:
    claims = result.get("claims") or []
    verdicts = [(c.get("outcome") or {}).get("verdict") or (c.get("outcome") or {}).get("kind") or "?" for c in claims]
    status = "TEXT" if "answer" in result else result.get("status") or "TECHNICAL_FAILURE"
    rejection = result.get("rejectionCategory")
    text = " ".join(filter(None, [body.text, body.url]))
    return {
        "check_id": result["checkId"], "channel": body.channel, "user_ref": body.user_ref,
        "conversation_id": body.conversation_id,
        "question": body.text[:MAX_TEXT_CHARS + 1] if body.text else None,  # za długi tekst - tylko początek
        "url": body.url[:2000] if body.url else None,
        "pii_masked": ",".join(pii) or None, "status": status, "verdicts": verdicts,
        "sources": [(e.get("source") or {}).get("url") for e in result.get("evidence") or []],
        "abstained": "INSUFFICIENT_EVIDENCE" in verdicts,
        "injection": rejection == "PROMPT_INJECTION" or bool(INJECTION_RE.search(text)),
        "rejection": rejection,
        "error": result.get("statusMessage") if status == "TECHNICAL_FAILURE" else None,
        "model": "/".join(filter(None, model_ref().values())) or None, "latency_ms": latency_ms,
        "cost_usd": stats.get("cost_usd"), "tokens_in": stats.get("tokens_in"), "tokens_out": stats.get("tokens_out"),
        "fetches": stats.get("fetches"), "fetch_errors": stats.get("fetch_errors"),
    }


async def _ask_agent(body: CheckIn, stats: dict) -> dict:
    if not (body.text or body.url):
        return failure("Brak treści do sprawdzenia.")
    if not AI_API_KEY or not AI_MODEL:
        return failure("Brak konfiguracji modelu (AI_API_KEY / AI_MODEL).")
    try:
        ask = server.ask(user_message(body), timeout=AGENT_TIMEOUT, is_final=is_final, stats=stats)
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
    report = _rate_limit(request, body) or await run_check(body)
    context = to_template_context(report, question=text)
    context["check_id"] = report.get("checkId")
    return templates.TemplateResponse(request, "result.html", context)


@app.post("/wynik/{check_id}/usun", response_class=HTMLResponse)
async def web_delete(check_id: str):
    """Przycisk "Usuń to sprawdzenie" pod wynikiem (HTMX): usuwa wpis z logu (FR-82)."""
    await asyncio.to_thread(checklog.delete, check_id)
    return HTMLResponse('<p class="result__deleted">Usunięto. Po tym sprawdzeniu nie ma śladu w naszym logu.</p>')


@app.get("/health")
async def health() -> dict:
    running = server.process is not None and server.process.poll() is None
    return {"status": "ok", "agentRunning": running, "model": model_ref(), "keySet": bool(AI_API_KEY),
            "allowedSources": len(allowed_patterns())}


@app.post("/api/v1/check")
async def check(request: Request, body: CheckIn):
    limited = _rate_limit(request, body)
    if limited:
        return JSONResponse(status_code=429, content=limited, headers={"Retry-After": str(limited["retryAfter"])})
    result = await run_check(body)
    if result.get("status") == "TECHNICAL_FAILURE":
        return JSONResponse(status_code=503, content=result)
    return result


@app.delete("/api/v1/checks/{check_id}")
async def delete_check(check_id: str):
    """Usunięcie sprawdzenia z logu (FR-82). Wystarczy znać checkId z wyniku - bez identyfikacji użytkownika."""
    deleted = await asyncio.to_thread(checklog.delete, check_id)
    return {"checkId": check_id, "deleted": deleted}


def _require_admin(request: Request) -> None:
    """Podgląd logu: z tokenem ADMIN_TOKEN (nagłówek Authorization: Bearer ...) albo, bez tokenu, tylko z tego komputera."""
    if ADMIN_TOKEN:
        given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not secrets.compare_digest(given, ADMIN_TOKEN):
            raise HTTPException(status_code=401, detail="Wymagany ADMIN_TOKEN.")
    elif not request.client or request.client.host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="Podgląd logu tylko z tego komputera albo z ADMIN_TOKEN.")


@app.get("/api/v1/log")
async def check_log(request: Request, limit: int = 50):
    """Log sprawdzeń dla zespołu i jury: podsumowanie (mediana czasu, koszt, wstrzymania, ataki) i ostatnie wpisy."""
    _require_admin(request)
    summary = await asyncio.to_thread(checklog.summary)
    entries = await asyncio.to_thread(checklog.recent, max(1, min(limit, 500)))
    return {"summary": summary, "checks": entries}


@app.get("/api/v1/log/{check_id}")
async def check_log_entry(request: Request, check_id: str):
    _require_admin(request)
    entry = await asyncio.to_thread(checklog.get, check_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Nie ma takiego sprawdzenia (mogło zostać usunięte).")
    return entry
