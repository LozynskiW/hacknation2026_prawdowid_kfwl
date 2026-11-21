from pydantic import BaseModel, Field


class Claim(BaseModel):
    """Pojedyncze twierdzenie wyodrębnione z zapytania (maks. 5 na zgłoszenie)."""

    claim_id: str = Field(
        description="Identyfikator twierdzenia (np. c1). Łączy twierdzenie z planem, dowodami i uwagami."
    )
    text: str = Field(description="Treść twierdzenia do sprawdzenia.")
    type: str = Field(
        description="Rodzaj twierdzenia: FACTUAL / OPINION / PREDICTION / QUESTION. "
        "OPINION i PREDICTION kończą się wynikiem NOT_CHECKABLE."
    )
    checkworthy: bool = Field(
        default=True, description="Czy twierdzenie nadaje się do sprawdzenia."
    )
    entities: list[str] = Field(
        default=[], description="Podmioty wymienione w twierdzeniu (instytucje, miejsca, osoby publiczne)."
    )
    time_ref: str = Field(
        default="",
        description="Odniesienie czasowe twierdzenia (kiedy ma zachodzić). "
        "Służy do wyznaczenia zakresu dat i oceny aktualności dowodów.",
    )
    place: str = Field(
        default="", description="Miejsce, którego dotyczy twierdzenie."
    )
    topic: str = Field(
        default="",
        description="Temat z taksonomii config/sources.yaml (np. pogoda, powódź, promieniowanie). "
        "Brak dopasowania = OUT_OF_SCOPE.",
    )


class CheckRequest(BaseModel):
    """M2 (intake) -> M3 (preselection). Zestandaryzowane zapytanie."""

    check_id: str = Field(description="Identyfikator sprawdzenia, wspólny dla całego przebiegu.")
    input_type: str = Field(description="Typ wejścia: TEXT / URL.")
    text_masked: str = Field(
        default="",
        description="Tekst zgłoszenia z zamaskowanymi danymi osobowymi (PESEL, telefon, e-mail, adres, "
        "imię i nazwisko osób prywatnych). Oryginał nie jest zapisywany.",
    )
    url: str = Field(default="", description="Link podany w zgłoszeniu.")
    claims: list[Claim] = Field(default=[], description="Twierdzenia do sprawdzenia, maks. 5.")
    flags: list[str] = Field(
        default=[],
        description="Flagi zgłoszenia, np. INJECTION_DETECTED (wykryto próbę wstrzyknięcia instrukcji), "
        "TRUNCATED_CLAIMS (obcięto listę twierdzeń do 5).",
    )
    status: str = Field(
        default="OK",
        description="Status całego zgłoszenia: OK / NEEDS_CLARIFICATION / OUT_OF_SCOPE / TECHNICAL_FAILURE. "
        "Inny niż OK kończy łańcuch i wynik idzie prosto do M7.",
    )
