"""Klient API PRAWDOWID.

Tryb podstawowy (synchroniczny):  POST /api/v1/check            → 200 + VerificationReport
Tryb awaryjny (asynchroniczny):  POST /api/v1/check            → 202 + {"checkId": ...}
                                 GET  /api/v1/checks/{checkId} → raport (status IN_PROGRESS = jeszcze trwa)

Każdy problem techniczny kończy się `CheckOutcome.failure` – nigdy werdyktem (scenariusz J).
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from .config import BotSettings
from .schemas import ReportView

log = logging.getLogger(__name__)

MSG_TIMEOUT = "Sprawdzenie trwa zbyt długo. Spróbuj ponownie za chwilę."
MSG_UNAVAILABLE = "Usługa sprawdzania jest chwilowo niedostępna. Spróbuj ponownie za chwilę."
MSG_RATE_LIMITED = "Zbyt wiele zapytań. Spróbuj ponownie za chwilę."
MSG_BAD_RESPONSE = "Usługa zwróciła nieprawidłową odpowiedź. Spróbuj ponownie później."


@dataclass(frozen=True)
class CheckOutcome:
    report: ReportView | None = None
    failure: str | None = None
    latency_ms: int = 0


class PrawdowidClient:
    def __init__(self, settings: BotSettings) -> None:
        self._s = settings
        headers = {"User-Agent": "prawdowid-discord-bot/0.1"}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key.get_secret_value()}"
        self._http = httpx.AsyncClient(
            base_url=settings.api_base_url,
            headers=headers,
            timeout=httpx.Timeout(settings.api_timeout_s, connect=5.0),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def check(self, *, text: str | None, url: str | None, user_ref: str, conversation_id: str) -> CheckOutcome:
        payload = {
            "channel": "DISCORD",
            "userRef": user_ref,
            "conversationId": conversation_id,
            "text": text,
            "url": url,
        }
        started = time.monotonic()
        try:
            async with asyncio.timeout(self._s.api_timeout_s):
                report, failure = await self._check(payload)
        except TimeoutError:
            report, failure = None, MSG_TIMEOUT
        latency = int((time.monotonic() - started) * 1000)
        log.info("check done conversation=%s latency_ms=%s ok=%s", conversation_id, latency, failure is None)
        return CheckOutcome(report=report, failure=failure, latency_ms=latency)

    async def _check(self, payload: dict) -> tuple[ReportView | None, str | None]:
        try:
            resp = await self._http.post("/api/v1/check", json=payload)
        except httpx.TimeoutException:
            return None, MSG_TIMEOUT
        except httpx.HTTPError as exc:
            log.warning("api unreachable: %s", type(exc).__name__)
            return None, MSG_UNAVAILABLE

        if resp.status_code == 202:
            check_id = _safe_json(resp).get("checkId")
            if not check_id:
                return None, MSG_BAD_RESPONSE
            return await self._poll(check_id)
        return self._parse(resp)

    async def _poll(self, check_id: str) -> tuple[ReportView | None, str | None]:
        while True:
            await asyncio.sleep(self._s.api_poll_interval_s)
            try:
                resp = await self._http.get(f"/api/v1/checks/{check_id}")
            except httpx.TimeoutException:
                return None, MSG_TIMEOUT
            except httpx.HTTPError:
                return None, MSG_UNAVAILABLE
            report, failure = self._parse(resp)
            if failure or (report and report.status != "IN_PROGRESS"):
                return report, failure

    @staticmethod
    def _parse(resp: httpx.Response) -> tuple[ReportView | None, str | None]:
        if resp.status_code == 429:
            return None, MSG_RATE_LIMITED
        body = _safe_json(resp)
        if resp.status_code >= 400:
            # Backend może zwrócić {"status": "TECHNICAL_FAILURE", "statusMessage": "..."}
            return None, body.get("statusMessage") or MSG_UNAVAILABLE
        try:
            return ReportView.model_validate(body), None
        except ValidationError as exc:
            log.warning("invalid report from api: %s errors", exc.error_count())
            return None, MSG_BAD_RESPONSE


def _safe_json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
