from pydantic import BaseModel


class Claim(BaseModel):
    claim_id: str
    text: str
    type: str  # FACTUAL / OPINION / PREDICTION / QUESTION
    checkworthy: bool = True
    entities: list[str] = []
    time_ref: str = ""
    place: str = ""
    topic: str = ""


class CheckRequest(BaseModel):
    """M2 -> M3: zestandaryzowane zapytanie."""

    check_id: str
    input_type: str  # TEXT / URL
    text_masked: str = ""
    url: str = ""
    claims: list[Claim] = []
    flags: list[str] = []
    status: str = "OK"  # OK / NEEDS_CLARIFICATION / OUT_OF_SCOPE / TECHNICAL_FAILURE
