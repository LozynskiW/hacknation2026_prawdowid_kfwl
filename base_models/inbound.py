from pydantic import BaseModel


class InboundMessage(BaseModel):
    """M1 -> verification: zgłoszenie z kanału."""

    channel: str  # WEB / DISCORD / WHATSAPP
    conversation_id: str
    text: str = ""
    url: str = ""
    received_at: str  # data ISO 8601
