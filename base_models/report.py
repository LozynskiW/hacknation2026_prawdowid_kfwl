from pydantic import BaseModel


class ClaimResult(BaseModel):
    claim_id: str
    text: str
    outcome: str  # VERDICT / NOT_CHECKABLE / NEEDS_CLARIFICATION / OUT_OF_SCOPE / TECHNICAL_FAILURE
    verdict: str = ""  # CONFIRMED / FALSE / MISLEADING / INSUFFICIENT_EVIDENCE
    strength: str = ""  # HIGH / MEDIUM / LOW
    explanation: str = ""
    evidence_ids: list[str] = []
    warnings: list[str] = []
    unknowns: list[str] = []
    grounding_score: float = 0.0


class VerificationReport(BaseModel):
    """M5 -> M6 -> M7: raport z werdyktami."""

    check_id: str
    claims: list[ClaimResult] = []
    review_decision: str = ""  # ACCEPT / RETRY / ABSTAIN
    remarks: list[list[str]] = []  # lista tur, w każdej lista uwag
    handoff: str = "NONE"  # NONE / RECOMMENDED / CASE_CREATED
