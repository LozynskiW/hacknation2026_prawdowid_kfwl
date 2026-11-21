from pydantic import BaseModel


class SourceCard(BaseModel):
    title: str
    publisher: str = ""
    url: str = ""
    published_at: str = ""
    quote: str = ""


class ClaimCard(BaseModel):
    claim_id: str
    text: str
    label: str  # np. "Potwierdzone", "Fałszywe"
    explanation: str = ""
    sources: list[SourceCard] = []
    warnings: list[str] = []
    unknowns: list[str] = []


class PresentationModel(BaseModel):
    """M7 -> M1: wynik gotowy do pokazania."""

    check_id: str
    channel: str
    summary: str = ""
    claims: list[ClaimCard] = []
    full_result_url: str = ""
