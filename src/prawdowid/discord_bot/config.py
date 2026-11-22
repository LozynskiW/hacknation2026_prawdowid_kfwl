"""Konfiguracja bota – wyłącznie ze zmiennych środowiskowych / pliku .env."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# .env z katalogu głównego repozytorium (src/prawdowid/discord_bot/config.py -> 3 poziomy wyżej),
# niezależnie od katalogu, z którego uruchomiono bota.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="", extra="ignore", env_ignore_empty=True)

    discord_token: SecretStr = Field(alias="DISCORD_TOKEN")
    # Gdy ustawione – komendy synchronizują się natychmiast na tym serwerze (wygodne w trakcie developmentu).
    discord_guild_id: int | None = Field(default=None, alias="DISCORD_GUILD_ID")
    # Czytanie zwykłych wiadomości na kanałach wymaga uprzywilejowanego "Message Content Intent".
    # Slash-komendy, wiadomości prywatne i oznaczenia bota działają bez niego.
    message_content_intent: bool = Field(default=False, alias="DISCORD_MESSAGE_CONTENT_INTENT")

    api_base_url: str = Field(default="http://localhost:8000", alias="PRAWDOWID_API_URL")
    api_key: SecretStr | None = Field(default=None, alias="PRAWDOWID_API_KEY")
    # Dłużej niż backend czeka na agenta (AGENT_TIMEOUT=300 s + 30 s zapasu), żeby bot nie przerywał
    # sprawdzenia, które backend jeszcze kończy. Token interakcji Discorda jest ważny 15 minut.
    api_timeout_s: float = Field(default=360.0, alias="PRAWDOWID_API_TIMEOUT")
    api_poll_interval_s: float = Field(default=2.0, alias="PRAWDOWID_API_POLL_INTERVAL")

    # Link do pełnego wyniku w WWW, np. https://prawdowid.example/wynik/{check_id}
    web_result_url_template: str | None = Field(default=None, alias="PRAWDOWID_WEB_RESULT_URL")

    # Sól do pseudonimizacji ID użytkownika (ID Discorda da się wyliczać, sam hash nie wystarcza).
    user_ref_salt: SecretStr = Field(alias="BOT_USER_SALT")

    # Prosty limit po stronie bota (backend ma własny).
    rate_limit_count: int = Field(default=3, alias="BOT_RATE_LIMIT_COUNT")
    rate_limit_window_s: float = Field(default=60.0, alias="BOT_RATE_LIMIT_WINDOW")
