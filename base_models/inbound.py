"""InboundMessage: M1 (access) -> verification."""

from datetime import datetime

from pydantic import AnyHttpUrl, Field, model_validator

from .base import SCHEMA_VERSION, ContractModel
from .enums import Channel

MAX_TEXT_LENGTH = 5000


class InboundMessage(ContractModel):
    """Surowe zgłoszenie z kanału (WWW / Discord / WhatsApp)."""

    schema_version: str = SCHEMA_VERSION
    channel: Channel
    conversation_id: str = Field(min_length=1)
    text: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    url: AnyHttpUrl | None = None  # tylko http/https, maks. 1 URL
    received_at: datetime

    @model_validator(mode="after")
    def _text_or_url(self) -> "InboundMessage":
        if not self.text and self.url is None:
            raise ValueError("Wymagany jest tekst lub URL.")
        return self
