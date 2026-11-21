from pydantic import BaseModel, Field


class ClaimSearch(BaseModel):
    """Plan wyszukiwania dla jednego twierdzenia."""

    claim_id: str = Field(description="Identyfikator twierdzenia, którego dotyczy plan.")
    queries: list[str] = Field(
        default=[],
        description="2-3 warianty zapytania (PL; EN tylko dla Fact Check API lub gdy temat zagraniczny).",
    )
    source_types: list[str] = Field(
        default=[],
        description="Typy źródeł do przeszukania: OFFICIAL / MEASUREMENT / FACT_CHECK. "
        "Zawsze dodawane jest źródło FACT_CHECK_API.",
    )
    hosts: list[str] = Field(
        default=[], description="Hosty z whitelisty przypisane do tematu twierdzenia (z katalogu źródeł)."
    )
    date_from: str = Field(
        default="",
        description="Początek zakresu dat (ISO 8601). Wynika z time_ref i okna aktualności typu informacji.",
    )
    date_to: str = Field(default="", description="Koniec zakresu dat (ISO 8601).")
    languages: list[str] = Field(default=["pl"], description="Języki wyszukiwania.")
    exclude_chunks: list[str] = Field(
        default=[], description="Fragmenty do pominięcia, odrzucone przez M6 akcją DROP_CHUNK."
    )


class SearchPlan(BaseModel):
    """M3 (preselection) -> M4 (retrieval). Gdzie i jak szukać dowodów."""

    check_id: str = Field(description="Identyfikator sprawdzenia.")
    round: int = Field(
        default=1, description="Numer tury wyszukiwania (maks. 2). Tura 2 tylko dla twierdzeń odrzuconych przez M6."
    )
    claims: list[ClaimSearch] = Field(
        default=[], description="Plany dla twierdzeń. Twierdzenia już zaakceptowane nie wchodzą do planu."
    )
