"""Ustawienia backendu - wyłącznie ze zmiennych środowiskowych / pliku .env.

  AI_PROVIDER=gemini             # gemini | mistral | anthropic | openai
  AI_API_KEY=...                 # klucz dostawcy, przekazywany tylko serwerowi OpenCode
  AI_MODEL=gemini-3.8-flash      # albo pełny identyfikator OpenCode, np. google/gemini-3.8-flash
                                 # Mistral: AI_PROVIDER=mistral, AI_MODEL=mistral-medium-latest
  OPENCODE_BIN=opencode2         # polecenie OpenCode V2 (pakiet npm @opencode/cli)
  AGENT_TIMEOUT=300              # ile sekund czekamy na odpowiedź agenta
  CHECK_LOG_DB=data/prawdowid.db # log sprawdzeń (SQLite)
  LOG_RETENTION_DAYS=7           # po ilu dniach wpisy logu są usuwane
  ADMIN_TOKEN=...                # dostęp do podglądu logu (/api/v1/log); bez niego tylko z tego komputera
  MAX_TEXT_CHARS=5000            # maks. długość sprawdzanego tekstu
  RATE_LIMIT_PER_MINUTE=5        # zapytania na osobę (IP strony / pseudonim z Discorda) na minutę
  RATE_LIMIT_GLOBAL_PER_MINUTE=30  # zapytania łącznie na minutę (chroni limit u dostawcy modelu)
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
AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "300"))
AGENT_DIR = ROOT / ".opencode"  # konfiguracja projektu OpenCode: agent, skille, uprawnienia
OPENCODE_DATA_DIR = _path("OPENCODE_DATA_DIR", "data/opencode")
WEB_DIR = PACKAGE / "web"
CHECK_LOG_DB = _path("CHECK_LOG_DB", "data/prawdowid.db")
LOG_RETENTION_DAYS = float(os.getenv("LOG_RETENTION_DAYS", "7"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "5000"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))
RATE_LIMIT_GLOBAL_PER_MINUTE = int(os.getenv("RATE_LIMIT_GLOBAL_PER_MINUTE", "30"))
