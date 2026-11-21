from pydantic import BaseModel, Field


class ClaimResult(BaseModel):
    """Wynik weryfikacji jednego twierdzenia."""

    claim_id: str = Field(description="Identyfikator twierdzenia.")
    text: str = Field(description="Treść twierdzenia.")
    outcome: str = Field(
        description="Rodzaj wyniku: VERDICT / NOT_CHECKABLE / NEEDS_CLARIFICATION / OUT_OF_SCOPE / "
        "TECHNICAL_FAILURE / CANNOT_CHECK."
    )
    verdict: str = Field(
        default="",
        description="Werdykt wyliczony regułami R0-R6 (nie przez LLM): CONFIRMED / FALSE / MISLEADING / "
        "INSUFFICIENT_EVIDENCE. Tylko gdy outcome = VERDICT.",
    )
    strength: str = Field(
        default="",
        description="Siła podstawy werdyktu: HIGH (>= 2 niezależne zgodne, w tym tier 1, brak przeciwnych) / "
        "MEDIUM (1 tier 1 lub 2 niezależne tier 2) / LOW (pozostałe).",
    )
    explanation: str = Field(
        default="",
        description="Wyjaśnienie w 1-3 zdaniach prostym polskim, wyłącznie na podstawie dowodów i werdyktu.",
    )
    evidence_ids: list[str] = Field(default=[], description="Identyfikatory dowodów, na których oparto wynik.")
    warnings: list[str] = Field(
        default=[],
        description="Ostrzeżenia (nigdy nie wpływają na werdykt): ARCHIVAL_MATERIAL, CONFLICTING_SOURCES, "
        "KNOWN_INCIDENT_MATCH, SOURCE_STATUS, REGIONAL_COVERAGE_LIMITED, PARTIAL_SEARCH.",
    )
    unknowns: list[str] = Field(default=[], description="Czego nie udało się ustalić.")
    grounding_score: float = Field(
        default=0.0,
        description="Ugruntowanie raportu w dowodach 0-1, liczone przez M6 (nie „prawda”). "
        ">= 0.75 = ACCEPT.",
    )


class VerificationReport(BaseModel):
    """M5 (reporting) -> M6 (review) -> M7 (presentation). Raport z wynikami twierdzeń."""

    check_id: str = Field(description="Identyfikator sprawdzenia.")
    claims: list[ClaimResult] = Field(default=[], description="Wyniki dla poszczególnych twierdzeń.")
    review_decision: str = Field(
        default="", description="Decyzja M6 (review): ACCEPT / RETRY / ABSTAIN."
    )
    remarks: list[list[str]] = Field(
        default=[],
        description="Uwagi M6. Indeks zewnętrzny = tura, lista wewnętrzna = uwagi z tury. Brak powtórek -> [].",
    )
    handoff: str = Field(
        default="NONE",
        description="Przekazanie do moderatora: NONE / RECOMMENDED / CASE_CREATED "
        "(CASE_CREATED tylko gdy sprawa faktycznie powstała).",
    )
