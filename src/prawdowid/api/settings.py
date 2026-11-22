"""Ustawienia backendu - wyłącznie ze zmiennych środowiskowych / pliku .env.

  AI_PROVIDER=gemini             # gemini | anthropic | openai
  AI_API_KEY=...                 # klucz dostawcy, przekazywany tylko serwerowi OpenCode
  AI_MODEL=gemini-3.8-flash      # albo pełny identyfikator OpenCode, np. google/gemini-3.8-flash
  OPENCODE_BIN=opencode2         # polecenie OpenCode V2 (pakiet npm @opencode/cli)
  AGENT_TIMEOUT=180              # ile sekund czekamy na odpowiedź agenta
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PACKAGE = Path(__file__).resolve().parents[1]  # src/prawdowid
ROOT = PACKAGE.parents[1]                       # katalog główny repozytorium


def _path(name: str, default: str) -> Path:
    path = Path(os.getenv(name) or default)
    return path if path.is_absolute() else ROOT / path


AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")
OPENCODE_BIN = os.getenv("OPENCODE_BIN", "opencode2")
AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "180"))
AGENT_DIR = ROOT / ".opencode"  # konfiguracja projektu OpenCode: agent, skille, uprawnienia
OPENCODE_DATA_DIR = _path("OPENCODE_DATA_DIR", "data/opencode")
WEB_DIR = PACKAGE / "web"
