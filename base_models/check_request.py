"""CheckRequest: M2 (intake) -> M3 (preselection)."""

from datetime import datetime

from pydantic import AnyHttpUrl, Field

from .base import SCHEMA_VERSION, ContractModel
from .enums import ClaimType, FetchStatus, InputType, RequestStatus, TimeRefKind

MAX_CLAIMS = 5


class FetchInfo(ContractModel):
    """Wynik pobrania strony wskazanej przez URL."""

    status: FetchStatus = FetchStatus.NOT_REQUESTED
    title: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None


class InputData(ContractModel):
    """Zestandaryzowane wejście (tekst już zamaskowany przez Guard)."""

    type: InputType
    raw_text_masked: str | None = None
    url: AnyHttpUrl | None = None
    fetch: FetchInfo = Field(default_factory=FetchInfo)


class TimeRef(ContractModel):
    """Odniesienie czasowe twierdzenia."""

    as_of: datetime | None = None
    kind: TimeRefKind = TimeRefKind.UNSPECIFIED


class Claim(ContractModel):
    """Pojedyncze twierdzenie do sprawdzenia."""

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    type: ClaimType
    checkworthy: bool
    entities: list[str] = Field(default_factory=list)
    time_ref: TimeRef = Field(default_factory=TimeRef)
    place: str | None = None
    topic: str | None = None  # None = brak dopasowania do taksonomii


class RequestFlags(ContractModel):
    injection_detected: bool = False
    pii_masked: bool = False
    truncated_claims: bool = False


class CheckRequest(ContractModel):
    schema_version: str = SCHEMA_VERSION
    check_id: str = Field(min_length=1)
    input: InputData
    claims: list[Claim] = Field(default_factory=list, max_length=MAX_CLAIMS)
    flags: RequestFlags = Field(default_factory=RequestFlags)
    status: RequestStatus = RequestStatus.OK
