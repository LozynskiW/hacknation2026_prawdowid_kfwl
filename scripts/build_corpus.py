"""Buduje korpus demonstracyjny PRAWDOWID z katalogu config/sources.yaml.

Uruchomienie (z katalogu repozytorium):
    python scripts/build_corpus.py            # wszystkie aktywne źródła
    python scripts/build_corpus.py --only govpl-rcb,cert-polska
    python scripts/build_corpus.py --no-full-text   # bez pobierania pełnych artykułów gov.pl

Wynik:
    data/corpus/documents.jsonl  - jeden dokument lub rekord na linię
    data/corpus/manifest.json    - podsumowanie: liczba dokumentów, domen, typów, błędy źródeł

Zasady:
    - pobieramy tylko źródła ze statusem ACTIVE i tylko w zakresie pola `storage` (licencja),
    - szanujemy robots.txt i robimy przerwę między zapytaniami do tego samego hosta,
    - błąd jednego źródła nie zatrzymuje budowy; trafia do manifestu,
    - każdy dokument ma datę publikacji (published_at) i pobrania (fetched_at).
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config" / "sources.yaml"
OUT_DIR = ROOT / "data" / "corpus"
USER_AGENT = "PrawdowidCorpusBuilder/0.1 (HackNation 2026; prototyp weryfikacji informacji)"
DELAY_S = 0.6          # przerwa między zapytaniami do tego samego hosta
TIMEOUT_S = 25
SUMMARY_MAX = 600      # maks. długość leadu przy storage=SUMMARY
FULL_TEXT_MAX = 20000  # maks. długość pełnego tekstu

_last_hit: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


# ------------------------------------------------------------------ HTTP

def _allowed(url: str) -> bool:
    """robots.txt czytamy naszym User-Agentem (domyślny parser Pythona przedstawia się inaczej i bywa blokowany).

    404 = brak ograniczeń. 401/403 lub błąd sieci = ostrożnie traktujemy jako zakaz pobierania.
    """
    parts = urllib.parse.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                rp.parse(r.read().decode("utf-8", "ignore").splitlines())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                rp.disallow_all = True
            else:
                rp.allow_all = True
        except Exception:
            rp.disallow_all = True
        _robots[base] = rp
    return _robots[base].can_fetch(USER_AGENT, url)


def fetch(url: str) -> bytes:
    if not _allowed(url):
        raise PermissionError(f"robots.txt nie pozwala pobrać {url}")
    host = urllib.parse.urlsplit(url).netloc
    wait = DELAY_S - (time.monotonic() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pl,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.read()
    finally:
        _last_hit[host] = time.monotonic()


def fetch_text(url: str) -> str:
    return fetch(url).decode("utf-8", "ignore")


# ------------------------------------------------------------------ pomocnicze

def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def clean(fragment: str) -> str:
    """HTML -> zwykły tekst w jednej linii."""
    fragment = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", fragment, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\s*\n\s*", "\n", text).strip()


def shorten(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def pl_date(value: str) -> str | None:
    """'20.11.2026' -> '2026-11-20'."""
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


PL_MONTHS = {"sty": "Jan", "lut": "Feb", "mar": "Mar", "kwi": "Apr", "maj": "May", "cze": "Jun",
             "lip": "Jul", "sie": "Aug", "wrz": "Sep", "paź": "Oct", "lis": "Nov", "gru": "Dec"}
PL_DAYS = {"pn": "Mon", "wt": "Tue", "śr": "Wed", "czw": "Thu", "pt": "Fri", "sob": "Sat", "nd": "Sun", "niedz": "Sun"}


def rss_date(value: str | None) -> str | None:
    if not value:
        return None
    # Niektóre kanały podają RFC 822 po polsku: "pt, 13 lis 2026 15:54:07 +0000".
    value = re.sub(r"^\s*(\w+),", lambda m: PL_DAYS.get(m.group(1).lower(), m.group(1)) + ",", value.strip())
    value = re.sub(r"\b(" + "|".join(PL_MONTHS) + r")\b", lambda m: PL_MONTHS[m.group(1)], value)
    try:
        return parsedate_to_datetime(value).astimezone(UTC).replace(microsecond=0).isoformat()
    except (TypeError, ValueError):
        pass
    m = re.match(r"\d{4}-\d{2}-\d{2}(T[\d:]+)?", value.strip())
    return m.group(0) if m else None


def make_doc(src: dict, *, url: str, title: str, text: str, published_at: str | None, **extra) -> dict:
    return {
        "id": hashlib.sha1(url.encode()).hexdigest()[:16],
        "source_id": src["id"],
        "publisher": src["publisher"],
        "type": src["type"],
        "tier": src["tier"],
        "role": src["role"],
        "topics": src.get("topics", []),
        "language": src.get("language", "pl"),
        "storage": src["storage"],
        "license": src["license"],
        "url": url,
        "host": urllib.parse.urlsplit(url).netloc,
        "title": title.strip(),
        "text": text,
        "published_at": published_at,
        "fetched_at": now_iso(),
        **extra,
    }


# ------------------------------------------------------------------ metody pobierania

def govpl_list(src: dict, full_text: bool) -> list[dict]:
    """Lista wiadomości gov.pl (bloki 'event' z datą, tytułem, leadem) + opcjonalnie pełny tekst artykułu."""
    docs = []
    for page in range(1, int(src.get("pages", 1)) + 1):
        page_url = src["url"] + (f"?page={page}" if page > 1 else "")
        body = fetch_text(page_url)
        for li in re.findall(r"<li>\s*(.*?)</li>", body, flags=re.S):
            link = re.search(r'<div class="title">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', li, flags=re.S)
            if not link:
                continue
            date = re.search(r'<span class="date">\s*([^<]+)', li)
            intro = re.search(r'<div class="intro">(.*?)</div>', li, flags=re.S)
            url = urllib.parse.urljoin("https://www.gov.pl", link.group(1))
            text = clean(intro.group(1)) if intro else ""
            published = pl_date(date.group(1)) if date else None
            if full_text and src["storage"] == "FULL_TEXT":
                try:
                    art = fetch_text(url)
                    m = re.search(r'class="editor-content">(.*?)<footer|class="editor-content">(.*?)</article>', art, flags=re.S)
                    if m:
                        body_text = clean(m.group(1) or m.group(2))
                        body_text = re.sub(r'\{"register".*$', "", body_text, flags=re.S).strip()  # resztka skryptu strony
                        text = shorten(body_text, FULL_TEXT_MAX)
                    if not published:  # brak daty na liście - bierzemy z artykułu
                        ev = re.search(r'class="event-date[^"]*"[^>]*>(.*?)</p>', art, flags=re.S)
                        published = pl_date(clean(ev.group(1))) if ev else None
                except Exception as e:  # pełny tekst niedostępny - zostaje lead
                    print(f"    ! {url}: {e}", file=sys.stderr)
            docs.append(make_doc(src, url=url, title=clean(link.group(2)), text=text, published_at=published))
    return docs


def rss(src: dict, full_text: bool) -> list[dict]:
    root = ET.fromstring(fetch(src["url"]))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    docs = []
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)
    for it in items:
        def get(tag: str) -> str | None:
            el = it.find(tag) if not tag.startswith("atom:") else it.find(tag, ns)
            return el.text if el is not None else None
        url = get("link") or ""
        if not url:
            el = it.find("atom:link", ns)
            url = el.get("href", "") if el is not None else ""
        title = get("title") or get("atom:title") or ""
        lead = get("description") or get("atom:summary") or ""
        published = rss_date(get("pubDate") or get("atom:published") or get("atom:updated")
                             or get("{http://purl.org/dc/elements/1.1/}date"))
        if url and title:
            docs.append(make_doc(src, url=url.strip(), title=clean(title),
                                 text=shorten(clean(lead), SUMMARY_MAX), published_at=published))
    return docs


def policja_list(src: dict, full_text: bool) -> list[dict]:
    body = fetch_text(src["url"])
    docs, seen = [], set()
    for href in re.findall(r'href="(/pol/aktualnosci/\d+,[^"]+\.html)"', body):
        if href in seen:
            continue
        seen.add(href)
        url = urllib.parse.urljoin(src["url"], href)
        art = fetch_text(url)
        title = re.search(r'property="og:title" content="([^"]*)"', art)
        lead = re.search(r'property="og:description" content="([^"]*)"', art)
        date = re.search(r"Data publikacji\s*([\d.]+)", art)
        docs.append(make_doc(src, url=url, title=clean(title.group(1)) if title else href,
                             text=shorten(clean(lead.group(1)), SUMMARY_MAX) if lead else "",
                             published_at=pl_date(date.group(1)) if date else None))
    return docs


def imgw_synop(src: dict, full_text: bool) -> list[dict]:
    rows = json.loads(fetch(src["url"]))
    docs = []
    for r in rows:
        observed = f"{r['data_pomiaru']}T{int(r['godzina_pomiaru']):02d}:00:00"
        text = (f"Stacja {r['stacja']}, pomiar {r['data_pomiaru']} godz. {r['godzina_pomiaru']}:00 UTC: "
                f"temperatura {r['temperatura']} °C, wiatr {r['predkosc_wiatru']} m/s (kierunek {r['kierunek_wiatru']}°), "
                f"wilgotność {r['wilgotnosc_wzgledna']} %, opad {r['suma_opadu']} mm, ciśnienie {r['cisnienie']} hPa.")
        url = f"https://danepubliczne.imgw.pl/api/data/synop/id/{r['id_stacji']}"
        docs.append(make_doc(src, url=url, title=f"Pomiar synoptyczny IMGW - {r['stacja']}", text=text,
                             published_at=observed, observed_at=observed, data=r))
    return docs


def gios_aq(src: dict, full_text: bool) -> list[dict]:
    listing = json.loads(fetch("https://api.gios.gov.pl/pjp-api/v1/rest/station/findAll?size=500"))
    stations = listing.get("Lista stacji pomiarowych", [])[: int(src.get("stations", 20))]
    docs = []
    for st in stations:
        sid = st["Identyfikator stacji"]
        url = src["url"].format(station=sid)
        try:
            data = json.loads(fetch(url)).get("AqIndex") or {}
        except Exception as e:
            print(f"    ! stacja {sid}: {e}", file=sys.stderr)
            continue
        level = data.get("Nazwa kategorii indeksu")
        when = data.get("Data wykonania obliczeń indeksu")
        if not level or not when:  # stacja bez bieżącego indeksu - brak danych do zapisania
            continue
        text = (f"Stacja {st['Nazwa stacji']} ({st.get('Nazwa miasta') or ''}): indeks jakości powietrza "
                f"\"{level}\" (obliczenie: {when or 'brak daty'}).")
        docs.append(make_doc(src, url=url, title=f"Indeks jakości powietrza GIOŚ - {st['Nazwa stacji']}", text=text,
                             published_at=when.replace(" ", "T") if when else None, observed_at=when, data=data))
    return docs


def nbp_rates(src: dict, full_text: bool) -> list[dict]:
    table = json.loads(fetch(src["url"]))[0]
    docs = []
    for r in table["rates"]:
        url = f"https://api.nbp.pl/api/exchangerates/rates/A/{r['code']}/{table['effectiveDate']}/?format=json"
        text = (f"Średni kurs NBP ({table['no']}, {table['effectiveDate']}): 1 {r['code']} ({r['currency']}) "
                f"= {r['mid']} PLN.")
        docs.append(make_doc(src, url=url, title=f"Kurs średni NBP - {r['code']}", text=text,
                             published_at=table["effectiveDate"], observed_at=table["effectiveDate"], data=r))
    return docs


def sejm_eli(src: dict, full_text: bool) -> list[dict]:
    year = datetime.now(UTC).year
    listing = json.loads(fetch(src["url"].format(year=year)))
    items = sorted(listing.get("items", []), key=lambda a: a.get("pos", 0), reverse=True)[: int(src.get("limit", 60))]
    docs = []
    for a in items:
        url = f"https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id={a['address']}"
        text = f"{a['displayAddress']}. {a['title']}. Status: {a.get('status', 'brak')}. Data ogłoszenia: {a.get('promulgation')}."
        docs.append(make_doc(src, url=url, title=a["title"], text=text,
                             published_at=a.get("promulgation") or a.get("announcementDate"), eli=a["address"]))
    return docs


METHODS = {"GOVPL_LIST": govpl_list, "RSS": rss, "POLICJA_LIST": policja_list,
           "IMGW_SYNOP": imgw_synop, "GIOS_AQ": gios_aq, "NBP_RATES": nbp_rates, "SEJM_ELI": sejm_eli}


# ------------------------------------------------------------------ główna funkcja

def registrable(host: str) -> str:
    """www.gov.pl -> gov.pl, ec.europa.eu -> europa.eu, pravda.org.pl -> pravda.org.pl."""
    parts = host.lower().split(".")
    if len(parts) >= 3 and parts[-2] in {"org", "com", "gov", "edu", "net"} and parts[-1] == "pl":
        return ".".join(parts[-3:]) if parts[-2] != "gov" else "gov.pl"
    return ".".join(parts[-2:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="lista id źródeł oddzielona przecinkami")
    ap.add_argument("--no-full-text", action="store_true", help="nie pobieraj pełnych artykułów (szybciej)")
    args = ap.parse_args()

    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["sources"]
    only = set(args.only.split(",")) if args.only else None
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    documents, report = [], []
    for src in catalog:
        if only and src["id"] not in only:
            continue
        if src["status"] != "ACTIVE" or src["method"] == "NONE":
            report.append({"id": src["id"], "status": src["status"], "documents": 0,
                           "reason": src.get("exclusion_reason", "")})
            continue
        print(f"- {src['id']} ({src['method']})", file=sys.stderr)
        started = time.monotonic()
        try:
            docs = METHODS[src["method"]](src, not args.no_full_text)
            error = None
        except Exception as e:  # źródło niedostępne - budujemy dalej
            docs, error = [], f"{type(e).__name__}: {e}"
            print(f"    ! {error}", file=sys.stderr)
        documents.extend(docs)
        report.append({"id": src["id"], "status": "OK" if error is None else "ERROR", "documents": len(docs),
                       "error": error, "seconds": round(time.monotonic() - started, 1)})

    # Ten sam adres z dwóch list = jeden dokument.
    unique = list({d["url"]: d for d in documents}.values())
    hosts = Counter(d["host"] for d in unique)
    manifest = {
        "built_at": now_iso(),
        "catalog": str(CATALOG.relative_to(ROOT)),
        "documents": len(unique),
        "hosts": len(hosts),
        "domains": len({registrable(h) for h in hosts}),
        "by_type": Counter(d["type"] for d in unique),
        "by_tier": Counter(str(d["tier"]) for d in unique),
        "by_host": dict(hosts.most_common()),
        "missing_published_at": sum(1 for d in unique if not d["published_at"]),
        "sources": report,
    }
    with (OUT_DIR / "documents.jsonl").open("w", encoding="utf-8") as f:
        for d in unique:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = manifest["documents"] >= 100 and manifest["domains"] >= 10 and len(manifest["by_type"]) >= 2
    print(f"\nDokumenty: {manifest['documents']}, hosty: {manifest['hosts']}, domeny: {manifest['domains']}, "
          f"typy: {dict(manifest['by_type'])}, bez daty publikacji: {manifest['missing_published_at']}", file=sys.stderr)
    print("Progi zadania (100 dokumentów, 10 domen, 2 typy): " + ("SPEŁNIONE" if ok else "NIESPEŁNIONE"), file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
