from pydantic import BaseModel


class ClaimSearch(BaseModel):
    claim_id: str
    queries: list[str] = []
    source_types: list[str] = []
    hosts: list[str] = []
    date_from: str = ""
    date_to: str = ""
    languages: list[str] = ["pl"]
    exclude_chunks: list[str] = []


class SearchPlan(BaseModel):
    """M3 -> M4: gdzie i jak szukać."""

    check_id: str
    round: int = 1
    claims: list[ClaimSearch] = []
