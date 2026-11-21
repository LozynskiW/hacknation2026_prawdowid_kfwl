"""Ustawienia backendu - wyłącznie ze zmiennych środowiskowych / pliku .env.

  AI_PROVIDER=gemini             # gemini | anthropic | openai (każde API zgodne z OpenAI)
  AI_API_KEY=...
  AI_MODEL=...
  AI_BASE_URL=                   # opcjonalnie, np. http://localhost:11434/v1 dla openai
  AGENT_DIR=agent                # definicja agenta i jego skille
  WHITELIST_FILE=config/whitelist.txt
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


AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "")
AGENT_DIR = _path("AGENT_DIR", "agent")
WHITELIST_FILE = _path("WHITELIST_FILE", "config/whitelist.txt")
WEB_DIR = PACKAGE / "web"
