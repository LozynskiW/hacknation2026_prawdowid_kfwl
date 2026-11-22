"""Zamiana odpowiedzi API na embedy Discorda.

Wynik ma wyglądać i czytać się jak na stronie WWW (templates/result.html):
- pierwszy embed: pytanie użytkownika, podsumowanie i zliczenie werdyktów,
- potem embed na każde twierdzenie: werdykt z pewnością, twierdzenie, krótka odpowiedź,
  uzasadnienie, źródła z cytatem, uwagi i to, czego nie udało się ustalić.

Zasady:
- bez logiki merytorycznej: bot tylko wybiera i skraca pola, nie zmienia treści,
- etykieta = tekst + ikona + kolor (nigdy sam kolor),
- statusy niewerdyktowe i awarie wyglądają inaczej niż werdykty (szare, bez werdyktu),
- limity Discorda: tytuł 256, opis 4096, pole 1024, maks. 25 pól, maks. 10 embedów
  i łącznie 6000 znaków na wiadomość.
"""

from datetime import datetime

import discord
from discord.utils import escape_markdown

from .api_client import CheckOutcome
from .schemas import ClaimView, EvidenceView, ReportView

MAX_TOTAL_CHARS = 5800  # zapas względem limitu 6000
MAX_CLAIM_EMBEDS = 5
MAX_SOURCES_PER_CLAIM = 3

FOOTER = "Wynik przygotował system z użyciem SI na podstawie wskazanych źródeł. Sprawdź źródła samodzielnie."

GREY = discord.Color.from_rgb(128, 134, 139)
GREEN = discord.Color.from_rgb(46, 160, 67)
RED = discord.Color.from_rgb(218, 54, 51)

VERDICTS: dict[str, tuple[str, str, discord.Color]] = {
    "CONFIRMED": ("✅", "Potwierdzone", GREEN),
    "FALSE": ("❌", "Fałszywe", RED),
    "MISLEADING": ("⚠️", "Wprowadza w błąd", discord.Color.from_rgb(219, 132, 0)),
    "INSUFFICIENT_EVIDENCE": ("❔", "Brak wystarczających dowodów", discord.Color.from_rgb(88, 101, 242)),
}

NON_VERDICTS: dict[str, tuple[str, str]] = {
    "NOT_CHECKABLE": ("💬", "Nie podlega weryfikacji (opinia lub prognoza)"),
    "NEEDS_CLARIFICATION": ("✏️", "Potrzebujemy doprecyzowania"),
    "OUT_OF_SCOPE": ("🚫", "Poza zakresem sprawdzania"),
    "TECHNICAL_FAILURE": ("🛠️", "Nie udało się teraz sprawdzić - to nie jest wynik sprawdzenia"),
    "CANNOT_CHECK": ("⏸️", "Nie udało się wykonać sprawdzenia"),
}

# Zliczenie werdyktów jak na stronie: "Sprawdzono 2 twierdzenia: 1 potwierdzone, 1 fałszywe."
SUMMARY_WORDS = {
    "CONFIRMED": "potwierdzone",
    "FALSE": "fałszywe",
    "MISLEADING": "wprowadzające w błąd",
    "INSUFFICIENT_EVIDENCE": "bez wystarczających dowodów",
    "NOT_CHECKABLE": "niepodlegające weryfikacji",
}

STRENGTH_PL = {"HIGH": "Mocna", "MEDIUM": "Średnia", "LOW": "Słaba"}
RECENCY_PL = {"CURRENT": "aktualne", "MIXED": "częściowo aktualne", "OUTDATED": "nieaktualne"}
TIER_PL = {1: "w tym źródło urzędowe lub pomiarowe", 2: "w tym fact-check", 3: "fact-check spoza IFCN/EFCSN"}
HANDOFF_PL = {
    "RECOMMENDED": "📨 Rekomendujemy przekazanie tego zgłoszenia analitykowi.",
    "CASE_CREATED": "📨 Zgłoszenie przekazano analitykowi.",
}


# ── API publiczne modułu ────────────────────────────────────────────────────


def render(outcome: CheckOutcome, full_result_url: str | None = None, question: str | None = None) -> list[discord.Embed]:
    """question - to, o co zapytał użytkownik (pokazywane na górze odpowiedzi, jak na stronie)."""
    if outcome.answer is not None:
        return answer_embeds(outcome.answer, question)
    if outcome.failure or outcome.report is None:
        return [failure_embed(outcome.failure or "Nie udało się wykonać sprawdzenia.", question)]
    report = outcome.report
    if report.status != "COMPLETED":
        return [_status_embed(report, question)]
    embeds = [_summary_embed(report, full_result_url, question)]
    evidence = report.evidence_by_id()
    for claim in report.claims[:MAX_CLAIM_EMBEDS]:
        embeds.append(_claim_embed(claim, evidence))
    embeds[-1].set_footer(text=FOOTER)
    return _fit_total(embeds)


def answer_embeds(text: str, question: str | None = None) -> list[discord.Embed]:
    """Odpowiedź modelu poza uzgodnionym formatem - jako zwykły tekst, podzielony po 3500 znaków."""
    head = _question_block(question)
    room = 3500
    budget = MAX_TOTAL_CHARS - len(head) - len(FOOTER) - 50  # tytuł i zapas
    text = _cut(text, budget)
    chunks = [text[i:i + room] for i in range(0, len(text), room)] or [""]
    embeds = [discord.Embed(title="🔎 Wynik sprawdzenia" if i == 0 else None,
                            description=(head + c) if i == 0 else c, color=GREY)
              for i, c in enumerate(chunks)]
    embeds[-1].set_footer(text=FOOTER)
    return embeds


def failure_embed(message: str, question: str | None = None) -> discord.Embed:
    icon, label = NON_VERDICTS["TECHNICAL_FAILURE"]
    e = discord.Embed(title=f"{icon} {label}", description=_question_block(question) + _cut(message, 1000), color=GREY)
    e.set_footer(text="Spróbuj ponownie za chwilę. Jeśli problem się powtarza, skontaktuj się z administratorem.")
    return e


def input_error_embed(message: str) -> discord.Embed:
    icon, label = NON_VERDICTS["NEEDS_CLARIFICATION"]
    return discord.Embed(title=f"{icon} {label}", description=_cut(message, 1000), color=GREY)


def help_embed() -> discord.Embed:
    e = discord.Embed(
        title="Prawdowid - jak to działa",
        description=(
            "Wyślij tekst lub link, a sprawdzę, co mówią na ten temat wiarygodne źródła "
            "(komunikaty urzędowe i dane publiczne z zamkniętej listy stron).\n\n"
            "**Jak użyć:** `/sprawdz tresc:… link:…`, wiadomość prywatna do bota albo oznaczenie bota.\n\n"
            "**Możliwe wyniki:** ✅ Potwierdzone · ❌ Fałszywe · ⚠️ Wprowadza w błąd · "
            "❔ Brak wystarczających dowodów · 💬 Nie podlega weryfikacji.\n\n"
            "Gdy dowodów nie ma, nie zgaduję - powiem, czego nie udało się ustalić.\n\n"
            "**Prywatność:** Twoje ID Discorda nie jest przekazywane - tylko jego pseudonim. "
            "Nie zapisujemy historii pytań."
        ),
        color=GREY,
    )
    e.set_footer(text=FOOTER)
    return e


# ── Budowa embedów ──────────────────────────────────────────────────────────


def _verdict_key(claim: ClaimView) -> str:
    return claim.outcome.verdict if claim.outcome.kind == "VERDICT" and claim.outcome.verdict else claim.outcome.kind


def _overall_color(report: ReportView) -> discord.Color:
    """Jak kolor oka na stronie: fałsz lub wprowadzanie w błąd - czerwony, same potwierdzenia - zielony, reszta szara."""
    keys = [_verdict_key(c) for c in report.claims]
    if any(k in ("FALSE", "MISLEADING") for k in keys):
        return RED
    if keys and all(k == "CONFIRMED" for k in keys):
        return GREEN
    return GREY


def _tally(report: ReportView) -> str:
    counts: dict[str, int] = {}
    for c in report.claims:
        key = _verdict_key(c)
        counts[key] = counts.get(key, 0) + 1
    total = len(report.claims)
    if not total:
        return ""
    parts = [f"{n} {SUMMARY_WORDS.get(k, k)}" for k, n in counts.items()]
    return f"Sprawdzono {total} {_claims_word(total)}: {', '.join(parts)}."


def _summary_embed(report: ReportView, full_result_url: str | None, question: str | None) -> discord.Embed:
    lines = []
    tally = _tally(report)
    if report.summary:
        lines.append(f"**Podsumowanie**\n{_cut(escape_markdown(report.summary), 1200)}")
    if tally and tally != report.summary:
        lines.append(f"-# {tally}")
    if len(report.claims) > MAX_CLAIM_EMBEDS:
        lines.append(f"Pokazuję {MAX_CLAIM_EMBEDS} pierwszych twierdzeń.")
    if report.handoff.status in HANDOFF_PL:
        lines.append(HANDOFF_PL[report.handoff.status])
    if full_result_url:
        lines.append(f"[Pełny wynik ze wszystkimi źródłami]({full_result_url})")
    description = _question_block(question) + "\n\n".join(lines)
    return discord.Embed(title="🔎 Wynik sprawdzenia", description=description, color=_overall_color(report))


def _status_embed(report: ReportView, question: str | None) -> discord.Embed:
    icon, label = NON_VERDICTS.get(report.status, NON_VERDICTS["CANNOT_CHECK"])
    msg = report.status_message or "Nie udało się wykonać sprawdzenia."
    description = _question_block(question) + _cut(escape_markdown(msg), 1500)
    e = discord.Embed(title=f"{icon} {label}", description=description, color=GREY)
    e.set_footer(text=FOOTER)
    return e


def _claim_embed(claim: ClaimView, evidence: dict[str, EvidenceView]) -> discord.Embed:
    key = _verdict_key(claim)
    icon, label = _badge(key)
    color = VERDICTS[key][2] if key in VERDICTS else GREY
    title = f"{icon} {label}"
    if claim.confidence is not None:
        title += f" · pewność {_percent(claim.confidence)}"

    parts = [f"### {_cut(escape_markdown(claim.text), 300)}"]
    if claim.short_answer:
        parts.append(f"**{_cut(escape_markdown(claim.short_answer), 300)}**")
    if claim.explanation:
        parts.append(f"**Uzasadnienie**\n{_cut(escape_markdown(claim.explanation), 900)}")
    e = discord.Embed(title=title, description="\n\n".join(parts), color=color)

    sources = [evidence[i] for i in claim.evidence_ids if i in evidence][:MAX_SOURCES_PER_CLAIM]
    if sources:
        e.add_field(name="Źródła", value=_cut("\n\n".join(_source_text(ev) for ev in sources), 1024), inline=False)

    if claim.strength and claim.strength.factors:
        e.add_field(name="Siła dowodów", value=_strength_text(claim), inline=False)

    if claim.warnings:
        e.add_field(
            name="Uwaga",
            value=_cut("\n".join(f"• {escape_markdown(w.message)}" for w in claim.warnings[:3]), 1024),
            inline=False,
        )
    if claim.unknowns:
        e.add_field(
            name="Czego nie udało się ustalić",
            value=_cut("\n".join(f"• {escape_markdown(u)}" for u in claim.unknowns[:3]), 1024),
            inline=False,
        )
    return e


def _strength_text(claim: ClaimView) -> str:
    s = claim.strength
    assert s is not None
    text = STRENGTH_PL.get(s.level, s.level)
    f = s.factors
    if not f:
        return text
    reasons = []
    if f.independent_sources:
        reasons.append(f"{f.independent_sources} {_plural_sources(f.independent_sources)}")
    if f.best_tier in TIER_PL:
        reasons.append(TIER_PL[f.best_tier])
    if f.recency in RECENCY_PL:
        reasons.append(RECENCY_PL[f.recency])
    if f.agreement == "CONFLICTING":
        reasons.append("źródła są ze sobą sprzeczne")
    return f"{text}: " + ", ".join(reasons) if reasons else text


def _source_text(ev: EvidenceView) -> str:
    src = ev.source
    date = _fmt_date(src.published_at)
    head = f"[{_cut(escape_markdown(src.title), 120)}]({src.url})"
    meta = escape_markdown(src.publisher) + (f" · {date}" if date else "")
    if ev.data_point:
        dp = ev.data_point
        when = _fmt_datetime(dp.observed_at)
        detail = f"Pomiar: {dp.value:g} {dp.unit}, {escape_markdown(dp.location)}" + (f", {when}" if when else "")
    elif ev.fact_check:
        detail = f"Ocena fact-checkera: „{escape_markdown(ev.fact_check.textual_rating)}”"
    elif ev.quote:
        detail = f"„{_cut(escape_markdown(ev.quote), 220)}”"
    else:
        detail = ""
    text = f"{head}\n-# {meta}"
    return f"{text}\n> {detail}" if detail else text


# ── Pomocnicze ──────────────────────────────────────────────────────────────


def _question_block(question: str | None) -> str:
    """Pytanie użytkownika na górze odpowiedzi (jak "Twoje pytanie" na stronie)."""
    if not question or not question.strip():
        return ""
    quoted = "\n".join(f"> {line}" for line in _cut(escape_markdown(question.strip()), 400).splitlines())
    return f"**Twoje pytanie**\n{quoted}\n\n"


def _badge(key: str) -> tuple[str, str]:
    if key in VERDICTS:
        icon, label, _ = VERDICTS[key]
        return icon, label
    return NON_VERDICTS.get(key, ("•", key))


def _percent(value: float) -> str:
    v = value * 100 if value <= 1 else value
    return f"{round(v)}%"


def _claims_word(n: int) -> str:
    if n == 1:
        return "twierdzenie"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "twierdzenia"
    return "twierdzeń"


def _plural_sources(n: int) -> str:
    if n == 1:
        return "niezależne źródło"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "niezależne źródła"
    return "niezależnych źródeł"


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _fmt_date(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y") if dt else ""


def _fmt_datetime(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else ""


def _fit_total(embeds: list[discord.Embed]) -> list[discord.Embed]:
    """Pilnuje łącznego limitu znaków wiadomości - w razie potrzeby usuwa pola od ostatniego embedu."""
    def total() -> int:
        return sum(len(e) for e in embeds)

    for e in reversed(embeds[1:]):
        while total() > MAX_TOTAL_CHARS and e.fields:
            e.remove_field(len(e.fields) - 1)
    while total() > MAX_TOTAL_CHARS and len(embeds) > 1:
        embeds.pop()
    if embeds and not embeds[-1].footer.text:
        embeds[-1].set_footer(text=FOOTER)
    return embeds
