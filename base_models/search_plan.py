"""SearchPlan: M3 (preselection) -> M4 (retrieval)."""

from datetime import datetime

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, ContractModel
from .enums import SourceType


class DateRange(ContractModel):
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None

    @model_validator(mode="after")
    def _order(self) -> "DateRange":
        if self.from_ and self.to and self.from_ > self.to:
            raise ValueError("Początek zakresu dat jest późniejszy niż koniec.")
        return self


class ClaimSearchPlan(ContractModel):
    """Plan wyszukiwania dla jednego twierdzenia."""

    claim_id: str = Field(min_length=1)
    queries: list[str] = Field(min_length=1, max_length=3)
    source_types: list[SourceType] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=list)
    date_range: DateRange = Field(default_factory=DateRange)
    languages: list[str] = Field(default_factory=lambda: ["pl"])
    exclude_chunks: list[str] = Field(default_factory=list)


class SearchPlan(ContractModel):
    schema_version: str = SCHEMA_VERSION
    check_id: str = Field(min_length=1)
    round: int = Field(default=1, ge=1, le=2)
    claims: list[ClaimSearchPlan] = Field(default_factory=list)
