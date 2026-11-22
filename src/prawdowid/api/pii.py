"""Maskowanie oczywistych danych osobowych (FR-80).

Tekst użytkownika przechodzi przez mask() zanim trafi do modelu i do logu sprawdzeń.
Dane zamieniamy na znaczniki, np. "[PESEL]", "[TELEFON]" - model wie, że coś tam było, ale nie widzi wartości.
Adresów URL nie ruszamy (liczby w adresach to zwykle identyfikatory stron, nie dane osobowe).
"""

import re

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

# Kolejność ma znaczenie: dłuższe i bardziej szczegółowe wzorce najpierw (konto przed telefonem itd.).
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # Numer konta (NRB 26 cyfr, opcjonalnie z PL i spacjami po 4 cyfry).
    ("NUMER_KONTA", re.compile(r"(?<![\w])(?:PL\s?)?\d{2}(?:[ ]?\d{4}){6}(?![\w])", re.IGNORECASE)),
    # Karta płatnicza: 13-19 cyfr, ze spacjami lub myślnikami, z poprawną sumą Luhna (sprawdzane niżej).
    ("KARTA", re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")),
    ("PESEL", re.compile(r"(?<!\d)\d{11}(?!\d)")),
    # Dowód osobisty: 3 litery i 6 cyfr (ABC123456), paszport: 2 litery i 7 cyfr.
    ("DOWOD", re.compile(r"(?<![\w])[A-Z]{3}\s?\d{6}(?![\w])")),
    ("PASZPORT", re.compile(r"(?<![\w])[A-Z]{2}\s?\d{7}(?![\w])")),
    # Telefon: 9 cyfr (z +48 / 0048 lub bez), z odstępami lub myślnikami.
    ("TELEFON", re.compile(r"(?<![\w+])(?:(?:\+|00)48[ -]?)?\d{3}[ -]?\d{3}[ -]?\d{3}(?!\d)")),
]


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total, alt = total + d, not alt
    return total % 10 == 0


def _pesel_ok(digits: str) -> bool:
    weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    return (10 - sum(int(d) * w for d, w in zip(digits, weights)) % 10) % 10 == int(digits[10])


def _mask_part(text: str, found: set[str]) -> str:
    for kind, pattern in PATTERNS:
        def repl(m: re.Match, kind=kind) -> str:
            raw = m.group(0)
            digits = re.sub(r"\D", "", raw)
            if kind == "KARTA" and not _luhn(digits):
                return raw
            if kind == "PESEL" and not _pesel_ok(digits):
                return raw
            found.add(kind)
            return f"[{kind}]"
        text = pattern.sub(repl, text)
    return text


def mask(text: str | None) -> tuple[str | None, list[str]]:
    """Zwraca (tekst z zamaskowanymi danymi, rodzaje znalezionych danych)."""
    if not text:
        return text, []
    found: set[str] = set()
    out, last = [], 0
    for m in URL_RE.finditer(text):  # adresy URL zostawiamy bez zmian
        out.append(_mask_part(text[last:m.start()], found))
        out.append(m.group(0))
        last = m.end()
    out.append(_mask_part(text[last:], found))
    return "".join(out), sorted(found)
