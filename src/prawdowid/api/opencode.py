"""Agent Prawdowid w OpenCode V2: backend uruchamia serwer OpenCode i wysyła mu pytania.

Serwer działa jako proces potomny backendu, tylko na 127.0.0.1, z losowym hasłem.
Serwer działa w katalogu głównym repozytorium, więc czyta konfigurację projektu z .opencode/:
agenta (agent/prawdowid.md), skille (skills/) i uprawnienia (opencode.jsonc).

Izolacja: serwer dostaje własny HOME i katalogi XDG w data/opencode/ oraz wyłączoną zgodność
z Claude Code, więc nie czyta globalnych instrukcji ani skilli użytkownika maszyny (~/.claude itd.).
Ze zmiennych środowiskowych dostaje tylko PATH i klucz dostawcy modelu.
"""

import asyncio
from collections.abc import Callable
import os
import secrets
import socket
import subprocess
from pathlib import Path

import httpx

from prawdowid.api.settings import (
    AI_API_KEY,
    AI_MODEL,
    AI_PROVIDER,
    OPENCODE_BIN,
    OPENCODE_DATA_DIR,
    ROOT,
)

AGENT_ID = "prawdowid"

# AI_PROVIDER -> (dostawca w OpenCode, zmienna z kluczem)
PROVIDERS = {
    "gemini": ("google", "GEMINI_API_KEY"),
    "anthropic": ("anthropic", "ANTHROPIC_API_KEY"),
    "openai": ("openai", "OPENAI_API_KEY"),
    "mistral": ("mistral", "MISTRAL_API_KEY"),
}


class AgentError(RuntimeError):
    """Agent nie oddał odpowiedzi (błąd serwera albo dostawcy modelu)."""

    def __init__(self, message: str, kind: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind  # np. "provider.quota" - wyczerpany limit u dostawcy


def model_ref() -> dict:
    """AI_PROVIDER=gemini, AI_MODEL=gemini-3.8-flash -> {"providerID": "google", "id": "gemini-3.8-flash"}."""
    if "/" in AI_MODEL:
        provider, model = AI_MODEL.split("/", 1)
        return {"providerID": provider, "id": model}
    return {"providerID": PROVIDERS.get(AI_PROVIDER, (AI_PROVIDER, ""))[0], "id": AI_MODEL}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class OpenCodeServer:
    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.url = ""
        self.password = ""

    def _env(self) -> dict[str, str]:
        home = OPENCODE_DATA_DIR / "home"
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(OPENCODE_DATA_DIR / "config"),
            "XDG_DATA_HOME": str(OPENCODE_DATA_DIR / "data"),
            "XDG_STATE_HOME": str(OPENCODE_DATA_DIR / "state"),
            "XDG_CACHE_HOME": str(OPENCODE_DATA_DIR / "cache"),
            "OPENCODE_SERVER_PASSWORD": self.password,
            "OPENCODE_DISABLE_CLAUDE_CODE": "1",
            "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "OPENCODE_DISABLE_FREE_MODELS": "1",
        }
        # Zmienna z kluczem wg dostawcy modelu (AI_MODEL może mieć prefiks, np. mistral/mistral-large-latest).
        provider = model_ref()["providerID"]
        key_var = next((var for pid, var in PROVIDERS.values() if pid == provider), None)
        if key_var and AI_API_KEY:
            env[key_var] = AI_API_KEY
        for path in (home, *(Path(env[k]) for k in env if k.startswith("XDG_"))):
            path.mkdir(parents=True, exist_ok=True)
        return env

    async def start(self, timeout: float = 60) -> None:
        if self.process and self.process.poll() is None:
            return
        port = _free_port()
        self.password = secrets.token_urlsafe(24)
        self.url = f"http://127.0.0.1:{port}"
        OPENCODE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        log = open(OPENCODE_DATA_DIR / "server.log", "ab")  # noqa: SIM115 - otwarty tak długo jak proces
        self.process = subprocess.Popen(
            [OPENCODE_BIN, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, env=self._env(), stdout=log, stderr=subprocess.STDOUT,
        )
        await self._wait_ready(timeout)

    async def _wait_ready(self, timeout: float) -> None:
        """Serwer odpowiada od razu, ale agent i skille wczytują się chwilę później."""
        deadline = asyncio.get_running_loop().time() + timeout
        async with self.client(timeout=5) as client:
            while asyncio.get_running_loop().time() < deadline:
                if self.process and self.process.poll() is not None:
                    raise AgentError(f"Serwer OpenCode zakończył się (kod {self.process.returncode}).")
                try:
                    r = await client.get("/api/agent")
                    if r.status_code == 200 and any(a.get("id") == AGENT_ID for a in r.json().get("data", [])):
                        return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.5)
        raise AgentError("Serwer OpenCode nie wczytał agenta na czas.")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.url, auth=("opencode", self.password), timeout=timeout)

    async def ask(self, text: str, timeout: float, is_final: Callable[[str], bool] = bool) -> str:
        """Nowa sesja na każde pytanie (bez historii), odpowiedź = tekst ostatniej wiadomości agenta.

        Stan sesji odpytujemy co sekundę zamiast czekać na /wait: przy błędzie dostawcy
        (np. wyczerpany limit) /wait potrafi wisieć do końca czasu, a wiadomość "idle" z błędem
        pojawia się od razu.
        """
        await self.start()
        deadline = asyncio.get_running_loop().time() + timeout
        async with self.client(timeout=30) as client:
            r = await client.post("/api/session", json={
                "agent": AGENT_ID, "model": model_ref(), "location": {"directory": str(ROOT)},
            })
            r.raise_for_status()
            session_id = r.json()["data"]["id"]
            try:
                answer = ""
                # Agent potrafi skończyć turę za wcześnie: pustym tekstem (Gemini po narzędziach)
                # albo wynikiem pośrednim skilla (np. samą walidacją wejścia). Wtedy ponaglamy.
                for prompt in (text, *[NUDGE] * MAX_NUDGES):
                    (await client.post(f"/api/session/{session_id}/prompt", json={"text": prompt})).raise_for_status()
                    answer = await self._wait_idle(client, session_id, deadline)
                    if answer and is_final(answer):
                        return answer
                if answer:
                    return answer
                raise AgentError("Agent nie zwrócił odpowiedzi.")
            finally:
                try:
                    await client.delete(f"/api/session/{session_id}")
                except httpx.HTTPError:
                    pass

    @staticmethod
    async def _wait_idle(client: httpx.AsyncClient, session_id: str, deadline: float) -> str:
        loop = asyncio.get_running_loop()
        seen = None
        while loop.time() < deadline:
            await asyncio.sleep(1)
            r = await client.get(f"/api/session/{session_id}/message", params={"order": "asc", "limit": "200"})
            r.raise_for_status()
            messages = r.json().get("data", [])
            if seen is None:  # pierwsze odczytanie: pomijamy "idle" z poprzedniej tury
                seen = max((i for i, m in enumerate(messages) if m.get("type") == "user"), default=0)
            if len(messages) > seen + 1 and messages[-1].get("type") == "idle":
                return _final_text(messages)
        await client.post(f"/api/session/{session_id}/interrupt")
        raise TimeoutError


MAX_NUDGES = 2
NUDGE = (
    "To nie jest końcowy raport. Dokończ procedurę (kroki 1-5) i zwróć końcowy raport "
    "jako jeden obiekt JSON w formacie ze skilla response-format."
)


def _final_text(messages: list[dict]) -> str:
    """Tekst ostatniej odpowiedzi agenta ("" gdy pusta). Tura zakończona błędem -> AgentError."""
    idle = messages[-1]
    if idle.get("outcome") != "succeeded":
        error = idle.get("error") or {}
        raise AgentError(error.get("message") or str(idle.get("outcome")), kind=error.get("type"))
    for m in reversed(messages):
        if m.get("type") == "user":
            break
        if m.get("type") == "assistant":
            text = "".join(c.get("text", "") for c in m.get("content") or [] if c.get("type") == "text").strip()
            if text:
                return text
    return ""


server = OpenCodeServer()
