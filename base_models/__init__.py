"""Podstawowe modele kontraktów PRAWDOWID (Pydantic v2).

Łańcuch: InboundMessage -> CheckRequest -> SearchPlan -> EvidenceSet
-> VerificationReport -> PresentationModel
"""

from .base import SCHEMA_VERSION, ContractModel
from .check_request import (
    MAX_CLAIMS,
    CheckRequest,
    Claim,
    FetchInfo,
    InputData,
    RequestFlags,
    TimeRef,
)
from .enums import (
    Channel,
    ClaimType,
    EvidenceType,
    FactCheckMatch,
    FetchStatus,
    HandoffStatus,
    InputType,
    OutcomeKind,
    RemarkAction,
    RemarkCode,
    RequestStatus,
    ReviewDecisionKind,
    SourceType,
    Stance,
    StrengthLevel,
    TemporalFit,
    TimeRefKind,
    Verdict,
    WarningCode,
)
from .evidence import DataPointValue, Evidence, EvidenceSet, SearchError, SourceRef
from .inbound import MAX_TEXT_LENGTH, InboundMessage
from .presentation import (
    OUTCOME_LABELS_PL,
    VERDICT_LABELS_PL,
    Badge,
    ClaimCard,
    PresentationModel,
    ReferralLink,
    SourceCard,
)
from .report import (
    CheckMetrics,
    ClaimOutcome,
    ClaimReport,
    Handoff,
    Remark,
    ReportWarning,
    ReviewSummary,
    Strength,
    VerificationReport,
)
from .search_plan import ClaimSearchPlan, DateRange, SearchPlan

__all__ = [
    "SCHEMA_VERSION", "ContractModel",
    "MAX_TEXT_LENGTH", "InboundMessage",
    "MAX_CLAIMS", "CheckRequest", "Claim", "FetchInfo", "InputData", "RequestFlags", "TimeRef",
    "ClaimSearchPlan", "DateRange", "SearchPlan",
    "DataPointValue", "Evidence", "EvidenceSet", "SearchError", "SourceRef",
    "CheckMetrics", "ClaimOutcome", "ClaimReport", "Handoff", "Remark", "ReportWarning",
    "ReviewSummary", "Strength", "VerificationReport",
    "OUTCOME_LABELS_PL", "VERDICT_LABELS_PL", "Badge", "ClaimCard", "PresentationModel",
    "ReferralLink", "SourceCard",
    "Channel", "ClaimType", "EvidenceType", "FactCheckMatch", "FetchStatus", "HandoffStatus",
    "InputType", "OutcomeKind", "RemarkAction", "RemarkCode", "RequestStatus",
    "ReviewDecisionKind", "SourceType", "Stance", "StrengthLevel", "TemporalFit",
    "TimeRefKind", "Verdict", "WarningCode",
]
