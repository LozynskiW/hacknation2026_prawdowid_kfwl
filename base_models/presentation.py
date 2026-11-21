from pydantic import BaseModel, Field


class SourceCard(BaseModel):
    """Karta źródła - wizualnie oddzielona od interpretacji systemu."""

    title: str = Field(description="Tytuł źródła.")
    publisher: str = Field(default="", description="Wydawca źródła.")
    url: str = Field(default="", description="Link do źródła.")
    published_at: str = Field(default="", description="Data publikacji (ISO 8601).")
    quote: str = Field(default="", description="Cytat lub wartość pomiaru ze źródła.")


class ClaimCard(BaseModel):
    """Karta twierdzenia w wyniku dla użytkownika."""

    claim_id: str = Field(description="Identyfikator twierdzenia.")
    text: str = Field(description="Treść twierdzenia.")
    label: str = Field(
        description="Etykieta wyniku po polsku: „Potwierdzone”, „Fałszywe”, „Wprowadza w błąd”, "
        "„Brak wystarczających dowodów”, „Nie podlega weryfikacji (opinia lub prognoza)”."
    )
    explanation: str = Field(default="", description="1-3 zdania wyjaśnienia z raportu.")
    sources: list[SourceCard] = Field(default=[], description="Karty źródeł dla twierdzenia.")
    warnings: list[str] = Field(default=[], description="Ostrzeżenia neutralnym językiem.")
    unknowns: list[str] = Field(default=[], description="„Czego nie udało się ustalić”.")


class PresentationModel(BaseModel):
    """M7 (presentation) -> M1 (access). Wynik czytelny dla obywatela."""

    check_id: str = Field(description="Identyfikator sprawdzenia.")
    channel: str = Field(description="Kanał docelowy (WEB / DISCORD / WHATSAPP), wybiera renderer.")
    summary: str = Field(default="", description="Podsumowanie: liczba twierdzeń i ich wyniki.")
    claims: list[ClaimCard] = Field(default=[], description="Karty twierdzeń.")
    full_result_url: str = Field(default="", description="Link do pełnego wyniku.")
