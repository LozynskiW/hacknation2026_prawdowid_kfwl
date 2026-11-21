from pydantic import BaseModel, Field


class InboundMessage(BaseModel):
    """M1 (access) -> verification. Zgłoszenie przyjęte z kanału, bez żadnej obróbki merytorycznej."""

    channel: str = Field(
        description="Kanał, z którego przyszło zgłoszenie: WEB / DISCORD / WHATSAPP."
    )
    conversation_id: str = Field(
        description="Identyfikator rozmowy w kanale. Wiąże odpowiedź użytkownika "
        "(np. doprecyzowanie) z poprzednim sprawdzeniem i wskazuje, gdzie dostarczyć wynik."
    )
    text: str = Field(
        default="",
        description="Tekst zgłoszenia od użytkownika. Maks. 5 000 znaków.",
    )
    url: str = Field(
        default="",
        description="Link do sprawdzenia. Maks. 1 URL, tylko http/https.",
    )
    received_at: str = Field(
        description="Czas przyjęcia zgłoszenia (ISO 8601)."
    )
