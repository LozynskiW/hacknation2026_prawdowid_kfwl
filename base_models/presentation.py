"""PresentationModel: M7 (presentation) -> M1 (access)."""

from datetime import datetime

from pydantic import AnyHttpUrl, Field

from .base import SCHEMA_VERSION, ContractModel
from .enums import Channel, HandoffStatus, OutcomeKind, Verdict

VERDICT_LABELS_PL: dict[Verdict, str] = {
    Verdict.CONFIRMED: "Potwierdzone",
    Verdict.FALSE: "Fałszywe",
    Verdict.MISLEADING: "Wprowadza w błąd",
    Verdict.INSUFFICIENT_EVIDENCE: "Brak wystarczających dowodów",
}

OUTCOME_LABELS_PL: dict[OutcomeKind, str] = {
    OutcomeKind.NOT_CHECKABLE: "Nie podlega weryfikacji (opinia lub prognoza)",
    OutcomeKind.NEEDS_CLARIFICATION: "Potrzebne doprecyzowanie",
    OutcomeKind.OUT_OF_SCOPE: "Poza zakresem",
    OutcomeKind.TECHNICAL_FAILURE: "Błąd techniczny",
    OutcomeKind.CANNOT_CHECK: "Nie można sprawdzić",
}


class Badge(ContractModel):
    """Etykieta wyniku: zawsze tekst + ikona + kolor (nigdy sam kolor)."""

    label: str
    icon: str
    color: str
    is_verdict: bool


class SourceCard(ContractModel):
    evidence_id: str
    title: str
    publisher: str
    url: AnyHttpUrl
    published_at: datetime | None = None
    fetched_at: datetime
    quote: str | None = None
    value: str | None = None  # sformatowana wartość pomiaru


class ClaimCard(ContractModel):
    claim_id: str
    text: str
    badge: Badge
    explanation: str | None = None
    strength_text: str | None = None
    sources: list[SourceCard] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    instruction: str | None = None  # dla statusów niewerdyktowych: co zrobić


class ReferralLink(ContractModel):
    """„Gdzie sprawdzić samodzielnie" - źródła z rolą REFERRAL."""

    title: str
    url: AnyHttpUrl


class PresentationModel(ContractModel):
    schema_version: str = SCHEMA_VERSION
    check_id: str = Field(min_length=1)
    channel: Channel
    summary: str
    claims: list[ClaimCard] = Field(default_factory=list)
    referrals: list[ReferralLink] = Field(default_factory=list)
    handoff_status: HandoffStatus = HandoffStatus.NONE
    handoff_text: str | None = None
    full_result_url: AnyHttpUrl | None = None
    footer: str | None = None
