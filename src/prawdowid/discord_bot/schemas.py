"""Widok odpowiedzi API (VerificationReport) po stronie bota.

Celowo tolerancyjny: ignoruje nieznane pola i przyjmuje nieznane wartości słowników jako tekst,
żeby rozszerzenie kontraktu po stronie backendu nie wywracało bota.
Kanoniczna definicja kontraktu: models/report.py.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class SourceView(_View):
    title: str
    publisher: str
    url: str
    source_type: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None


class DataPointView(_View):
    metric: str
    value: float
    unit: str
    location: str
    observed_at: datetime | None = None


class FactCheckView(_View):
    textual_rating: str
    review_date: datetime | None = None


class EvidenceView(_View):
    evidence_id: str
    type: str
    source: SourceView
    quote: str | None = None
    data_point: DataPointView | None = None
    fact_check: FactCheckView | None = None
    stance: str | None = None


class OutcomeView(_View):
    kind: str
    verdict: str | None = None


class StrengthFactorsView(_View):
    best_tier: int | None = None
    independent_sources: int = 0
    recency: str | None = None
    agreement: str | None = None


class StrengthView(_View):
    level: str
    factors: StrengthFactorsView | None = None


class WarningView(_View):
    code: str
    message: str


class ClaimView(_View):
    claim_id: str
    text: str
    outcome: OutcomeView
    strength: StrengthView | None = None
    short_answer: str = ""
    confidence: float | None = None
    relevance: int = 3
    explanation: str = ""
    evidence_ids: list[str] = []
    warnings: list[WarningView] = []
    unknowns: list[str] = []


class HandoffView(_View):
    status: str = "NONE"
    case_id: str | None = None


class ReportView(_View):
    check_id: str | None = None
    status: str
    status_message: str | None = None
    original_message: str | None = None
    overall_verdict: str | None = None
    verdict_counts: dict[str, int] = {}
    summary: str = ""
    claims: list[ClaimView] = []
    evidence: list[EvidenceView] = []
    handoff: HandoffView = HandoffView()

    def evidence_by_id(self) -> dict[str, EvidenceView]:
        return {e.evidence_id: e for e in self.evidence}
