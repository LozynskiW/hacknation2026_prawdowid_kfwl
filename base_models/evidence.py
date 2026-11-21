from pydantic import BaseModel


class Evidence(BaseModel):
    evidence_id: str
    claim_id: str
    type: str  # QUOTE / DATA_POINT / FACT_CHECK_REVIEW
    source_title: str = ""
    source_publisher: str = ""
    source_url: str = ""
    published_at: str = ""
    fetched_at: str = ""
    tier: int = 0
    quote: str = ""
    stance: str = ""  # SUPPORTS / REFUTES / PARTIAL / CONTEXT / IRRELEVANT
    relevance: float = 0.0


class EvidenceSet(BaseModel):
    """M4 -> M5: znalezione dowody."""

    check_id: str
    evidence: list[Evidence] = []
    search_errors: list[str] = []
