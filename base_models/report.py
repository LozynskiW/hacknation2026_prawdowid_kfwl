"""VerificationReport: M5 (reporting) -> M6 (review) -> M7 (presentation)."""

from typing import Any

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, ContractModel
from .enums import (
    HandoffStatus,
    OutcomeKind,
    RemarkAction,
    RemarkCode,
    ReviewDecisionKind,
    StrengthLevel,
    Verdict,
    WarningCode,
)


class Remark(ContractModel):
    """Uwaga M6 dla kolejnej tury wyszukiwania."""

    claim_id: str
    code: RemarkCode
    message: str
    action: RemarkAction
    params: dict[str, Any] | None = None
    chunk_id: str | None = None


class ClaimOutcome(ContractModel):
    kind: OutcomeKind
    verdict: Verdict | None = None

    @model_validator(mode="after")
    def _verdict_only_for_verdict_kind(self) -> "ClaimOutcome":
        if (self.kind == OutcomeKind.VERDICT) != (self.verdict is not None):
            raise ValueError("verdict jest wymagany tylko i wyłącznie dla kind=VERDICT.")
        return self


class Strength(ContractModel):
    level: StrengthLevel
    factors: list[str] = Field(default_factory=list)


class ReportWarning(ContractModel):
    code: WarningCode
    message: str


class ClaimReport(ContractModel):
    claim_id: str = Field(min_length=1)
    text: str
    outcome: ClaimOutcome
    strength: Strength | None = None
    explanation: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    warnings: list[ReportWarning] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    grounding_score: float | None = Field(default=None, ge=0.0, le=1.0)


class ReviewSummary(ContractModel):
    decision: ReviewDecisionKind | None = None
    rounds: int = Field(default=0, ge=0, le=2)


class Handoff(ContractModel):
    status: HandoffStatus = HandoffStatus.NONE
    case_id: str | None = None
    reason: str | None = None


class CheckMetrics(ContractModel):
    duration_ms: int | None = Field(default=None, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_estimate: float | None = Field(default=None, ge=0.0)


class VerificationReport(ContractModel):
    schema_version: str = SCHEMA_VERSION
    check_id: str = Field(min_length=1)
    claims: list[ClaimReport] = Field(default_factory=list)
    review: ReviewSummary = Field(default_factory=ReviewSummary)
    # indeks zewnętrzny = tura, lista wewnętrzna = uwagi z tury; brak powtórek -> []
    remarks: list[list[Remark]] = Field(default_factory=list)
    handoff: Handoff = Field(default_factory=Handoff)
    metrics: CheckMetrics = Field(default_factory=CheckMetrics)
    corpus_version: str | None = None
    pipeline_version: str | None = None
