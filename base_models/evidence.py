from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Pojedynczy dowód dla twierdzenia."""

    evidence_id: str = Field(description="Identyfikator dowodu, wskazywany w raporcie (evidence_ids).")
    claim_id: str = Field(description="Identyfikator twierdzenia, którego dotyczy dowód.")
    type: str = Field(
        description="Typ dowodu: QUOTE (cytat z fragmentu korpusu) / DATA_POINT (pomiar) / "
        "FACT_CHECK_REVIEW (recenzja z Fact Check API)."
    )
    source_title: str = Field(default="", description="Tytuł dokumentu źródłowego.")
    source_publisher: str = Field(default="", description="Wydawca źródła.")
    source_url: str = Field(default="", description="URL źródła.")
    published_at: str = Field(default="", description="Data publikacji źródła (ISO 8601).")
    fetched_at: str = Field(default="", description="Data pobrania źródła (ISO 8601).")
    tier: int = Field(
        default=0, description="Poziom wiarygodności źródła z katalogu (1 = najwyższy). Silny dowód to tier <= 2."
    )
    quote: str = Field(
        default="",
        description="Dosłowny fragment z chunka (lub wartość pomiaru). M6 sprawdza, czy występuje w źródle.",
    )
    stance: str = Field(
        default="",
        description="Stanowisko dowodu wobec twierdzenia: SUPPORTS / REFUTES / PARTIAL / CONTEXT / IRRELEVANT.",
    )
    relevance: float = Field(
        default=0.0, description="Trafność dowodu 0-1. Dowody poniżej 0.5 są odrzucane przed regułami."
    )


class EvidenceSet(BaseModel):
    """M4 (retrieval) -> M5 (reporting). Dowody znalezione dla twierdzeń."""

    check_id: str = Field(description="Identyfikator sprawdzenia.")
    evidence: list[Evidence] = Field(default=[], description="Znalezione dowody.")
    search_errors: list[str] = Field(
        default=[],
        description="Błędy wyszukiwania (źródło, kod, komunikat, np. MISSING_API_KEY). "
        "Błąd jednego źródła nie zatrzymuje pozostałych.",
    )
