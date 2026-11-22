"""Walidacja wejścia (FR-52) i limit zapytań (FR-53) - po stronie backendu, dla każdego kanału.

Formularz WWW i bot mają własne limity, ale API można wywołać bezpośrednio (np. skryptem),
więc backend sprawdza wszystko jeszcze raz, zanim zapytanie trafi do agenta (i zacznie kosztować).

Limit zapytań działa w pamięci procesu (okno 60 s): na osobę (pseudonim z Discorda albo adres IP
dla strony) i łącznie na cały system. Adresów IP nigdzie nie zapisujemy - po minucie znikają.
"""

import re
import time
from collections import defaultdict, deque

from prawdowid.api.settings import MAX_TEXT_CHARS, RATE_LIMIT_GLOBAL_PER_MINUTE, RATE_LIMIT_PER_MINUTE

MAX_URL_CHARS = 2000
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
WINDOW_S = 60.0


def validate(text: str | None, url: str | None) -> str | None:
    """Komunikat dla użytkownika, gdy wejście jest nieprawidłowe; None, gdy wszystko w porządku."""
    text, url = (text or "").strip(), (url or "").strip()
    if not text and not url:
        return "Wpisz informację do sprawdzenia albo wklej link."
    if len(text) > MAX_TEXT_CHARS:
        return (f"Tekst jest za długi ({len(text)} znaków, maks. {MAX_TEXT_CHARS}). "
                "Wklej najważniejszy fragment - ten, który budzi wątpliwości.")
    if url and (len(url) > MAX_URL_CHARS or not URL_RE.fullmatch(url)):
        return "Link musi zaczynać się od http:// lub https:// i być pojedynczym adresem strony."
    return None


class RateLimiter:
    """Okno przesuwne: maks. `per_key` zapytań na klucz i `total` łącznie w ciągu WINDOW_S sekund."""

    def __init__(self, per_key: int = RATE_LIMIT_PER_MINUTE, total: int = RATE_LIMIT_GLOBAL_PER_MINUTE) -> None:
        self.per_key, self.total = per_key, total
        self._keys: dict[str, deque[float]] = defaultdict(deque)
        self._all: deque[float] = deque()

    def _trim(self, window: deque[float], now: float) -> None:
        while window and now - window[0] >= WINDOW_S:
            window.popleft()

    def hit(self, key: str) -> int | None:
        """Rejestruje zapytanie. Zwraca None, gdy wolno, albo liczbę sekund do ponownej próby."""
        now = time.monotonic()
        window = self._keys[key]
        self._trim(window, now)
        self._trim(self._all, now)
        if self.per_key and len(window) >= self.per_key:
            return int(WINDOW_S - (now - window[0])) + 1
        if self.total and len(self._all) >= self.total:
            return int(WINDOW_S - (now - self._all[0])) + 1
        window.append(now)
        self._all.append(now)
        if len(self._keys) > 10_000:  # sprzątanie pustych kluczy, żeby pamięć nie rosła
            for k in [k for k, w in self._keys.items() if not w]:
                del self._keys[k]
        return None


def rate_limited_message(retry_after: int) -> str:
    return f"Za dużo zapytań w krótkim czasie. Spróbuj ponownie za {retry_after} s."
