"""Spis serwisów instytucji na www.gov.pl - lista dozwolonych źródeł dla skilla weryfikacji.

Uruchomienie (z katalogu repozytorium):
    python scripts/govpl_sites.py                 # wynik: config/govpl_whitelist.json
    python scripts/govpl_sites.py --limit 50      # szybki test

Skąd lista:
    1. Katalog jednostek gov.pl (https://www.gov.pl/web/gov/katalog-jednostek) - pełny spis portalu.
    2. Serwisy, do których linkują strony główne jednostek i ich podstrony typu
       "jednostki podległe", "stacje", "komendy" (np. powiatowe stacje sanitarno-epidemiologiczne).

Jeden wpis = jeden serwis (https://www.gov.pl/web/<jednostka>). Wpis obejmuje wszystkie podstrony serwisu.

Format wpisu:
    {"linkDoStrony": ..., "krótkiOpisZawartości": ..., "tagi": [...], "licencja": ...}
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "govpl_whitelist.json"
BASE = "https://www.gov.pl"
CATALOG = BASE + "/web/gov/katalog-jednostek"
USER_AGENT = "PrawdowidCorpusBuilder/0.1 (HackNation 2026; prototyp weryfikacji informacji)"
DELAY_S = 0.5

LICENSE = (
    "Treści tekstowe gov.pl: CC BY-SA 4.0 (uznanie autorstwa - na tych samych warunkach); "
    "zdjęcia, audio i wideo: CC BY-NC-ND 4.0, o ile nie zaznaczono inaczej; "
    "materiały urzędowe można wykorzystywać bez zgody (art. 4 ustawy o prawie autorskim); "
    "utwory osób trzecich wymagają zgody właściciela. Źródło: https://www.gov.pl/web/gov/prawa-autorskie"
)

# Serwisy techniczne portalu - nie są źródłem treści.
SKIP = {"gov", "jednostka-nie-ma-swojej-witryny"}

# Pozycje menu, które nie mówią nic o treści serwisu.
ADMIN_MENU = re.compile(
    r"^(o (nas|urzędzie|ministerstwie|stacji|wsse|psse|instytucji|komendzie|prokuraturze)|dyrekcja|kierownictwo|historia|"
    r"kariera|praca|oferty pracy|zamówienia publiczne|przetargi|dostępność|deklaracja dostępności|kontakt|dane kontaktowe|"
    r"struktura|struktura organizacyjna|biura i departamenty|departamenty i biura|zadania instytucji|zadania|"
    r"informacje publiczne|bip|biuletyn informacji publicznej|rodo|ochrona danych osobowych|mapa strony|"
    r"strona główna|szukaj|english|en|ua)$", re.I)

# Podstrony, na których szukamy jednostek podległych.
CHILD_PAGES = re.compile(r"jednostk|podleg|nadzorowan|terenow|stacj|komend|delegatur|oddział|placówk|inspektorat|izb", re.I)

# Słowa w nazwie i menu -> tagi tematyczne (taksonomia z docs/MODULY.md).
TAG_RULES = [
    (r"sanitarn|epidemiolog|zdrow|szpital|lekar|farmac|chorób|medyc", ["zdrowie"]),
    (r"straż[yа]? pożarn|psp|pożar|ratownic", ["bezpieczeństwo publiczne", "straż pożarna"]),
    (r"prokurat", ["prawo", "prokuratura"]),
    (r"sąd|sprawiedliw|więziennict", ["prawo"]),
    (r"wojewódz|wojewoda", ["administracja regionalna"]),
    (r"polska w |ambasad|konsulat|przedstawicielstw|dyplomac|zagranicz", ["dyplomacja", "podróże", "sytuacja międzynarodowa"]),
    (r"(?<!cyber)bezpieczeństw|kryzys|\brcb\b|alarm|ostrzeż", ["bezpieczeństwo publiczne", "ostrzeżenia"]),
    (r"obron|wojsk|armi|żołnierz", ["obronność"]),
    (r"atom|radiac|promieniow", ["promieniowanie"]),
    (r"cyfryz|cyber|informaty", ["cyber"]),
    (r"dezinform", ["dezinformacja"]),
    (r"klimat|środowisk|ochrony środowiska|powietrz|odpad", ["środowisko"]),
    (r"wod[ya]? polsk|hydro|powodz|powódź|gospodarki wodnej", ["powódź", "woda"]),
    (r"\bdróg\b|\bdrogi\b|drogow|gddkia|autostrad", ["drogi"]),
    (r"kolej|transport|lotnic|lotnisk|morsk|żeglug|infrastrukt", ["transport"]),
    (r"rolnict|weteryn|fitosanit|nasien|żywnoś|rolno-spoż|arimr|krus", ["rolnictwo"]),
    (r"finans|skarb|podatk|celn|budżet", ["finanse"]),
    (r"edukac|kurator|szkoł|nauk|uczel", ["edukacja", "nauka"]),
    (r"rodzin|pracy i polityki|społeczn|zus|emerytur|senior", ["sprawy społeczne"]),
    (r"\bkultur|dziedzictw|zabytk|\bsport|turyst", ["kultura i sport"]),
    (r"energ|paliw|gaz", ["energia"]),
    (r"statysty|dane publiczne|geodez|kartograf", ["dane publiczne"]),
    (r"policj|spraw wewnętrznych|mswia|migrac|cudzoziem|straż graniczn", ["bezpieczeństwo publiczne"]),
    (r"komunikat|ostrzeżen|meldunk|alert", ["komunikaty"]),
    (r"aktualnoś|wiadomoś", ["aktualności"]),
]

_last = 0.0


def fetch(url: str) -> tuple[str, str] | None:
    """Zwraca (końcowy adres, HTML) albo None przy błędzie."""
    global _last
    wait = DELAY_S - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pl"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.geturl(), r.read().decode("utf-8", "ignore")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        print(f"    ! {url}: {e}", file=sys.stderr)
        return None
    finally:
        _last = time.monotonic()


def text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def slug_of(href: str) -> str | None:
    """https://www.gov.pl/web/rcb/komunikaty -> rcb; https://www.gov.pl/ijhars -> ijhars (skrót)."""
    m = re.match(r"^(?:https?://www\.gov\.pl)?/(?:web/)?([a-z0-9][a-z0-9-]*)(?:[/?#].*)?$", href.strip())
    if not m or m.group(1) in {"attachment", "photo", "scripts", "styles", "fonts", "img", "api", "web"}:
        return None
    return m.group(1)


def catalog_units() -> dict[str, str]:
    """slug -> kategoria z katalogu jednostek gov.pl."""
    res = fetch(CATALOG)
    if not res:
        sys.exit("Nie udało się pobrać katalogu jednostek gov.pl")
    _, body = res
    units: dict[str, str] = {}
    for block in re.split(r'<h3 id="[^"]*"><button[^>]*>', body)[1:]:
        category = text(block.split("</button>")[0])
        for href in re.findall(r'<h4 id="[^"]*"><a href="([^"]+)"', block) + re.findall(r'class="accordion-link" href="([^"]+)"', block):
            if "www.gov.pl" in href and (s := slug_of(href)) and s not in SKIP:
                units.setdefault(s, category)
    return units


def unit_name(page: str, slug: str) -> str:
    m = re.search(r'property="og:title"\s*content="([^"]*)"', page) or re.search(r"<title>(.*?)</title>", page, re.S)
    raw = re.sub(r"\s*-?\s*Portal Gov\.pl\s*$", "", html.unescape(m.group(1) if m else slug))
    parts = [p.strip() for p in re.split(r"\s+-\s+", raw)]
    parts = [p for p in parts if p and p.lower() not in {"gov.pl", "strona główna"}
             and not p.lower().startswith("strona główna")]
    return max(dict.fromkeys(parts), key=len) if parts else slug


class _MenuParser(HTMLParser):
    """Drzewo menu serwisu (#unit-menu-list): [(tytuł, href, [(tytuł dziecka, href)])]."""

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0          # zagnieżdżenie <ul> wewnątrz menu (1 = pierwszy poziom)
        self.inside = False
        self.items: list[tuple[str, str, list[tuple[str, str]]]] = []
        self._href: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "ul" and a.get("id") == "unit-menu-list":
            self.inside, self.depth = True, 1
        elif self.inside and tag == "ul":
            self.depth += 1
        elif self.inside and tag == "a":
            self._href, self._buf = a.get("href", ""), []

    def handle_endtag(self, tag):
        if self.inside and tag == "a" and self._href is not None:
            title = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if title:
                if self.depth == 1:
                    self.items.append((title, self._href, []))
                elif self.items:
                    self.items[-1][2].append((title, self._href))
            self._href = None
        elif self.inside and tag == "ul":
            self.depth -= 1
            if self.depth == 0:
                self.inside = False

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)


def unit_menu(page: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
    p = _MenuParser()
    p.feed(page)
    return p.items


ACTIVITY_MENU = re.compile(r"co robimy|działalność|zadania|dla obywatela|informacje dla|tematy|sprawy|obszary", re.I)


def content_sections(menu, name: str) -> tuple[list[str], list[str]]:
    """(sekcje pierwszego poziomu bez administracyjnych, pozycje z działu 'Co robimy' / 'Działalność')."""
    top = [t for t, _, _ in menu if not ADMIN_MENU.match(t) and t != name and len(t) <= 60]
    activity = [c for t, _, kids in menu if ACTIVITY_MENU.search(t) for c, _ in kids
                if not ADMIN_MENU.match(c) and len(c) <= 80]
    return list(dict.fromkeys(top)), list(dict.fromkeys(activity))


def group_name(page: str) -> str | None:
    m = re.search(r'href="/web/gov/katalog-jednostek\?catalogId=[^"]*"\s*title="([^"]+)"', page)
    return html.unescape(m.group(1)) if m else None


STATUS_TAGS = {"komunikaty", "aktualności"}

# Placówki zagraniczne - także w wersjach obcojęzycznych (nazwa sekcji "Embassy", "Botschaft", "Посольство"...).
EMBASSY = re.compile(
    r"embassy|ambassad|embajad|embaixad|botschaft|посольств|пасольств|посолств|velvyslan|veleposlan|veľvyslan|nagykövet|"
    r"vēstniec|suurlähetyst|sendiráð|elçilik|elchixona|səfirlik|大使|대사관|πρεσβεία|đại sứ|consulat|konsulat|консульств", re.I)


def make_tags(category: str | None, name: str, top: list[str], activity: list[str]) -> list[str]:
    """Tematy - z nazwy jednostki i jej działalności; 'komunikaty'/'aktualności' - tylko z pierwszego poziomu menu."""
    tags = [category] if category else []
    topical = " ".join([name, *activity]).lower()
    menu_top = " ".join(top).lower()
    for pattern, add in TAG_RULES:
        status = set(add) <= STATUS_TAGS
        if re.search(pattern, menu_top if status else topical):
            tags.extend(add)
    if EMBASSY.search(" ".join([name, *top, *activity])):
        tags.extend(["dyplomacja", "podróże", "sytuacja międzynarodowa"])
    country = re.match(r"^Polska w (.+)$", name)
    if country:
        tags.append(f"kraj: {country.group(1)}")
    if is_foreign(name, top):
        tags.append("wersja obcojęzyczna")
    return list(dict.fromkeys(t for t in tags if t))


POLISH_WORDS = re.compile(r"aktualnoś|wiadomoś|kontakt|informacj|co robimy|załatw|o nas|ogłoszeni|komunikat", re.I)


def is_foreign(name: str, top: list[str]) -> bool:
    """Serwis w innym języku niż polski (np. wersja angielska ministerstwa, strona placówki po niemiecku)."""
    sample = " ".join([name, *top])
    return not re.search(r"[ąćęłńśźż]", sample, re.I) and not POLISH_WORDS.search(sample)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=3000, help="maks. liczba serwisów")
    args = ap.parse_args()

    units = catalog_units()
    print(f"Katalog: {len(units)} serwisów", file=sys.stderr)
    queue = deque(units)
    seen = set(units)
    entries, skipped = [], []

    while queue and len(entries) + len(skipped) < args.limit:
        slug = queue.popleft()
        url = f"{BASE}/web/{slug}"
        res = fetch(url)
        if not res:
            skipped.append({"slug": slug, "reason": "błąd pobrania"})
            continue
        final, page = res
        final_slug = slug_of(final.replace(BASE, ""))
        if final.rstrip("/") == BASE or not final_slug or final_slug in SKIP:
            skipped.append({"slug": slug, "reason": f"przekierowanie na {final}"})
            continue
        if final_slug != slug and final_slug in seen:  # alias innego serwisu
            continue
        seen.add(final_slug)

        name = unit_name(page, final_slug)
        menu = unit_menu(page)
        top, activity = content_sections(menu, name)
        category = units.get(slug) or group_name(page)
        description = f"Serwis: {name}."
        if activity:
            description += f" Działalność: {', '.join(activity[:5])}."
        if top:
            description += f" Sekcje: {', '.join(top[:5])}."
        entries.append({
            "linkDoStrony": f"{BASE}/web/{final_slug}",
            "krótkiOpisZawartości": description[:400],
            "tagi": make_tags(category, name, top, activity),
            "licencja": LICENSE,
        })
        print(f"  [{len(entries):4}] {final_slug}: {name}", file=sys.stderr)

        # Szukamy kolejnych serwisów: linki ze strony głównej i z podstron typu "jednostki podległe".
        found = {s for h in re.findall(r'href="((?:https?://www\.gov\.pl)?/web/[a-z0-9-]+)[/"]', page) if (s := slug_of(h))}
        for t, h in [(c, ch) for _, _, kids in menu for c, ch in kids] + [(t, h) for t, h, _ in menu]:
            if CHILD_PAGES.search(t) and "www.gov.pl" in (h if h.startswith("http") else BASE + h):
                sub = fetch(h if h.startswith("http") else BASE + h)
                if sub:
                    found |= {s for x in re.findall(r'href="((?:https?://www\.gov\.pl)?/web/[a-z0-9-]+)[/"]', sub[1])
                              if (s := slug_of(x))}
        for s in sorted(found - seen - SKIP):
            seen.add(s)
            queue.append(s)

    entries.sort(key=lambda e: e["linkDoStrony"])
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nZapisano {len(entries)} serwisów do {OUT.relative_to(ROOT)}; pominięto {len(skipped)}; "
          f"w kolejce zostało {len(queue)}", file=sys.stderr)
    for s in skipped:
        print(f"  - pominięto {s['slug']}: {s['reason']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
