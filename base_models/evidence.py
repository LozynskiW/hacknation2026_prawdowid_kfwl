"""EvidenceSet: M4 (retrieval) -> M5 (reporting)."""

from datetime import datetime

from pydantic import AnyHttpUrl, Field, model_validator

from .base import SCHEMA_VERSION, ContractModel
from .enums import EvidenceType, FactCheckMatch, Stance, TemporalFit


class SourceRef(ContractModel):
    """Metadane źródła dowodu."""

    title: str
    publisher: str
    url: AnyHttpUrl
    published_at: datetime | None = None
    fetched_at: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observed_at: datetime | None = None
    tier: int = Field(ge=1, le=4)


class DataPointValue(ContractModel):
    value: float
    unit: str | None = None
    area: str | None = None


class Evidence(ContractModel):
    """Pojedynczy dowód dla twierdzenia."""

    evidence_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    type: EvidenceType
    chunk_id: str | None = None  # QUOTE
    data_point_id: str | None = None  # DATA_POINT
    review_url: AnyHttpUrl | None = None  # FACT_CHECK_REVIEW
    source: SourceRef
    quote: str | None = None
    value: DataPointValue | None = None
    textual_rating: str | None = None  # FACT_CHECK_REVIEW
    stance: Stance
    match: FactCheckMatch | None = None
    relevance: float = Field(ge=0.0, le=1.0)
    temporal_fit: TemporalFit | None = None
    independence_key: str | None = None

    @model_validator(mode="after")
    def _ref_matches_type(self) -> "Evidence":
        required = {
            EvidenceType.QUOTE: ("chunk_id", "quote"),
            EvidenceType.DATA_POINT: ("data_point_id", "value"),
            EvidenceType.FACT_CHECK_REVIEW: ("review_url",),
        }[self.type]
        missing = [name for name in required if getattr(self, name) is None]
        if missing:
            raise ValueError(f"Dowód typu {self.type} wymaga pól: {', '.join(missing)}")
        return self


class SearchError(ContractModel):
    """Błąd jednego źródła - nie zatrzymuje pozostałych."""

    source: str
    code: str  # np. MISSING_API_KEY, TIMEOUT
    message: str
    claim_id: str | None = None


class EvidenceSet(ContractModel):
    schema_version: str = SCHEMA_VERSION
    check_id: str = Field(min_length=1)
    round: int = Field(default=1, ge=1, le=2)
    evidence: list[Evidence] = Field(default_factory=list)
    search_errors: list[SearchError] = Field(default_factory=list)
