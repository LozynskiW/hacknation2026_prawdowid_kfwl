"""Zamiana odpowiedzi API na embedy Discorda.

Zasady:
- bez logiki merytorycznej: bot tylko wybiera i skraca pola, nie zmienia treści,
- etykieta = tekst + ikona + kolor (nigdy sam kolor),
- statusy niewerdyktowe i awarie wyglądają inaczej niż werdykty,
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
MAX_SOURCES_PER_CLAIM = 2

FOOTER = "Wynik przygotował system z użyciem SI na podstawie wskazanych źródeł. Sprawdź źródła samodzielnie."

GREY = discord.Color.from_rgb(128, 134, 139)

VERDICTS: dict[str, tuple[str, str, discord.Color]] = {
    "CONFIRMED": ("✅", "Potwierdzone", discord.Color.from_rgb(46, 160, 67)),
    "FALSE": ("❌", "Fałszywe", discord.Color.from_rgb(218, 54, 51)),
    "MISLEADING": ("⚠️", "Wprowadza w błąd", discord.Color.from_rgb(219, 132, 0)),
    "INSUFFICIENT_EVIDENCE": ("❔", "Brak wystarczających dowodów", discord.Color.from_rgb(88, 101, 242)),
}

NON_VERDICTS: dict[str, tuple[str, str]] = {
    "NOT_CHECKABLE": ("💬", "Nie podlega weryfikacji (opinia lub prognoza)"),
    "NEEDS_CLARIFICATION": ("✏️", "Potrzebujemy doprecyzowania"),
    "OUT_OF_SCOPE": ("🚫", "Poza zakresem usługi"),
    "TECHNICAL_FAILURE": ("🛠️", "Błąd techniczny – to nie jest wynik sprawdzenia"),
    "CANNOT_CHECK": ("⏸️", "Nie udało się wykonać sprawdzenia"),
}

STRENGTH_PL = {"HIGH": "Mocna", "MEDIUM": "Średnia", "LOW": "Słaba"}
RECENCY_PL = {"CURRENT": "aktualne", "MIXED": "częściowo aktualne", "OUTDATED": "nieaktualne"}
TIER_PL = {1: "w tym źródło urzędowe lub pomiarowe", 2: "w tym fact-check", 3: "fact-check spoza IFCN/EFCSN"}
HANDOFF_PL = {
    "RECOMMENDED": "📨 Rekomendujemy przekazanie tego zgłoszenia analitykowi.",
    "CASE_CREATED": "📨 Zgłoszenie przekazano analitykowi.",
}


# ── API publiczne modułu ────────────────────────────────────────────────────


def render(outcome: CheckOutcome, full_result_url: str | None = None) -> list[discord.Embed]:
    if outcome.answer is not None:
        return answer_embeds(outcome.answer)
    if outcome.failure or outcome.report is None:
        return [failure_embed(outcome.failure or "Nie udało się wykonać sprawdzenia.")]
    report = outcome.report
    if report.status != "COMPLETED":
        return [_status_embed(report)]
    embeds = [_summary_embed(report, full_result_url)]
    evidence = report.evidence_by_id()
    for claim in report.claims[:MAX_CLAIM_EMBEDS]:
        embeds.append(_claim_embed(claim, evidence))
    return _fit_total(embeds)


def answer_embeds(text: str) -> list[discord.Embed]:
    """Odpowiedź modelu jako tekst (Markdown), podzielona na embedy po 4000 znaków."""
    chunks = [text[i:i + 4000] for i in range(0, min(len(text), MAX_TOTAL_CHARS), 4000)] or [""]
    embeds = [discord.Embed(title="🔎 Wynik sprawdzenia" if i == 0 else None, description=c, color=GREY)
              for i, c in enumerate(chunks)]
    embeds[-1].set_footer(text=FOOTER)
    return embeds


def failure_embed(message: str) -> discord.Embed:
    icon, label = NON_VERDICTS["TECHNICAL_FAILURE"]
    e = discord.Embed(title=f"{icon} {label}", description=_cut(message, 1000), color=GREY)
    e.set_footer(text="Spróbuj ponownie za chwilę. Jeśli problem się powtarza, skontaktuj się z administratorem.")
    return e


def input_error_embed(message: str) -> discord.Embed:
    icon, label = NON_VERDICTS["NEEDS_CLARIFICATION"]
    return discord.Embed(title=f"{icon} {label}", description=_cut(message, 1000), color=GREY)


def help_embed() -> discord.Embed:
    e = discord.Embed(
        title="Prawdowid – jak to działa",
        description=(
            "Wyślij tekst lub link, a sprawdzę, co mówią na ten temat wiarygodne źródła "
            "(komunikaty urzędowe, dane publiczne, organizacje fact-checkingowe).\n\n"
            "**Jak użyć:** `/sprawdz tresc:… link:…`, wiadomość prywatna do bota albo oznaczenie bota.\n\n"
            "**Możliwe wyniki:** ✅ Potwierdzone · ❌ Fałszywe · ⚠️ Wprowadza w błąd · "
            "❔ Brak wystarczających dowodów · 💬 Nie podlega weryfikacji.\n\n"
            "Gdy dowodów nie ma, nie zgaduję – powiem, czego nie udało się ustalić.\n\n"
            "**Prywatność:** dane osobowe są maskowane, a Twoje ID Discorda nie jest przekazywane – "
            "tylko jego pseudonim."
        ),
        color=GREY,
    )
    e.set_footer(text=FOOTER)
    return e


# ── Budowa embedów ──────────────────────────────────────────────────────────


def _summary_embed(report: ReportView, full_result_url: str | None) -> discord.Embed:
    counts: dict[str, int] = {}
    for c in report.claims:
        key = c.outcome.verdict if c.outcome.kind == "VERDICT" and c.outcome.verdict else c.outcome.kind
        counts[key] = counts.get(key, 0) + 1
    parts = []
    for key, n in counts.items():
        icon, label = _badge(key)
        parts.append(f"{icon} {label}: **{n}**")

    lines = [f"Sprawdzone twierdzenia: **{len(report.claims)}**", " · ".join(parts)]
    if len(report.claims) > MAX_CLAIM_EMBEDS:
        lines.append(f"Pokazuję {MAX_CLAIM_EMBEDS} pierwszych – pełny wynik pod linkiem.")
    if report.handoff.status in HANDOFF_PL:
        lines.append(HANDOFF_PL[report.handoff.status])
    if full_result_url:
        lines.append(f"[Pełny wynik ze wszystkimi źródłami]({full_result_url})")

    e = discord.Embed(title="🔎 Wynik sprawdzenia", description="\n".join(lines), color=GREY)
    e.set_footer(text=FOOTER)
    return e


def _status_embed(report: ReportView) -> discord.Embed:
    icon, label = NON_VERDICTS.get(report.status, NON_VERDICTS["CANNOT_CHECK"])
    msg = report.status_message or "Nie udało się wykonać sprawdzenia."
    e = discord.Embed(title=f"{icon} {label}", description=_cut(escape_markdown(msg), 1500), color=GREY)
    e.set_footer(text=FOOTER)
    return e


def _claim_embed(claim: ClaimView, evidence: dict[str, EvidenceView]) -> discord.Embed:
    key = claim.outcome.verdict if claim.outcome.kind == "VERDICT" and claim.outcome.verdict else claim.outcome.kind
    icon, label = _badge(key)
    color = VERDICTS[key][2] if key in VERDICTS else GREY

    description = f"**Twierdzenie:** „{_cut(escape_markdown(claim.text), 300)}”"
    if claim.explanation:
        description += f"\n\n{_cut(escape_markdown(claim.explanation), 500)}"
    e = discord.Embed(title=f"{icon} {label}", description=description, color=color)

    if claim.strength:
        e.add_field(name="Siła dowodów", value=_strength_text(claim), inline=False)

    sources = [evidence[i] for i in claim.evidence_ids if i in evidence][:MAX_SOURCES_PER_CLAIM]
    if sources:
        e.add_field(name="Źródła", value=_cut("\n\n".join(_source_text(ev) for ev in sources), 1024), inline=False)

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
    head = f"[{_cut(escape_markdown(src.title), 120)}]({src.url}) — {escape_markdown(src.publisher)}"
    if date:
        head += f", {date}"
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
    return f"{head}\n> {detail}" if detail else head


# ── Pomocnicze ──────────────────────────────────────────────────────────────


def _badge(key: str) -> tuple[str, str]:
    if key in VERDICTS:
        icon, label, _ = VERDICTS[key]
        return icon, label
    return NON_VERDICTS.get(key, ("•", key))


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
    """Pilnuje łącznego limitu znaków wiadomości – w razie potrzeby usuwa pola od ostatniego embedu."""
    def total() -> int:
        return sum(len(e) for e in embeds)

    for e in reversed(embeds[1:]):
        while total() > MAX_TOTAL_CHARS and e.fields:
            e.remove_field(len(e.fields) - 1)
    while total() > MAX_TOTAL_CHARS and len(embeds) > 1:
        embeds.pop()
    return embeds
