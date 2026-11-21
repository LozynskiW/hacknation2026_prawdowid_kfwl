# Źródła PRAWDOWID

Lista źródeł, z których może korzystać skill weryfikacji, razem z licencjami i zasadami ich kwalifikacji. Pełny katalog do audytu: [`config/sources.yaml`](../config/sources.yaml). Hosty dopuszczone jako dowód (filtr w `app_simple`): [`config/whitelist.txt`](../config/whitelist.txt).

## Wymagania zadania i stan

Zadanie (sekcja 5, „Źródła”): korpus demonstracyjny min. **100 dokumentów lub rekordów**, min. **10 domen**, co najmniej **dwa typy źródeł** (pierwotne lub urzędowe + wiarygodne wtórne), lista dostępna do audytu.

Pomiar z `scripts/build_corpus.py` (2026-11-21):

| Miernik | Wymóg | Wynik |
|---|---|---|
| Dokumenty i rekordy | ≥ 100 | **658** |
| Domeny (główne, np. `gov.pl`, `europa.eu`) | ≥ 10 | **10** (13 hostów) |
| Typy źródeł | ≥ 2 | **4**: urzędowe 451, pomiary 107, akty prawne 60, fact-checking 40 |
| Dokumenty z datą publikacji i pobrania | wymóg „Aktualność” | 656 z 658 |

Odtworzenie wyniku:

```bash
python scripts/build_corpus.py
```

Wynik trafia do `data/corpus/` (`documents.jsonl` + `manifest.json`, poza repozytorium). Skrypt kończy się kodem 1, jeśli progi nie są spełnione.

## Zasady kwalifikacji

Źródło trafia do katalogu, gdy spełnia wszystkie warunki:

1. **Wydawca jest wiarygodny:**
   - **źródła pierwotne i urzędowe:** administracja rządowa (gov.pl), służby, instytuty pomiarowe (IMGW, GIOŚ), NBP, Dziennik Ustaw, instytucje UE i WHO,
   - **źródła wtórne:** organizacje fact-checkingowe zweryfikowane według standardów IFCN lub EFCSN albo huby sieci EDMO.
2. **Wolno pobierać treść:** `robots.txt` na to pozwala i serwis nie blokuje automatów. Nie obchodzimy zabezpieczeń (wymóg z sekcji 5 zadania).
3. **Znamy podstawę prawną:** przechowujemy tylko tyle, ile pozwala licencja (pole `storage`):
   - **pełny tekst** tylko przy jawnej licencji (gov.pl: CC BY-SA 4.0),
   - **przy braku jawnej licencji:** tytuł, lead z RSS i link,
   - **dane pomiarowe i akty prawne:** jako rekordy, bo dane urzędowe i akty normatywne nie są utworami.
4. **Każdy dokument ma** wydawcę, tytuł, link, datę publikacji i datę pobrania.

Status źródła ani domena nie przesądzają o prawdziwości konkretnego twierdzenia. Poziom (`tier`: 1 = urzędowe/pierwotne, 2 = wtórne) służy tylko do oceny siły dowodu.

## Aktualizacja i wykluczanie

- **Częstotliwość odświeżania:** pole `refresh`, od 1 godziny (ostrzeżenia, pomiary) do 1 dnia (akty prawne, raporty).
- **Błędy pobierania:** błąd jednego źródła nie zatrzymuje budowy korpusu. Trafia do `manifest.json` i jest widoczny przy audycie.
- **Wykluczenie:** źródło dostaje `status: EXCLUDED` z powodem w `exclusion_reason`, gdy:
  - zabrania pobierania (`robots.txt`, HTTP 403),
  - nie mamy licencji,
  - przestaje spełniać zasady kwalifikacji.

  Źródło wykluczone może zostać jako „sprawdź sam” (`role: REFERRAL`), ale nigdy nie jest dowodem.
- **Nowe źródło:** wpis w `config/sources.yaml` plus jego adres w `config/whitelist.txt`, po sprawdzeniu punktów 1-4.

## Źródła aktywne

| id | Wydawca | Typ | Poziom | Co przechowujemy | Dokumenty | Licencja / podstawa |
|---|---|---|---|---|---|---|
| `govpl-rcb` | Rządowe Centrum Bezpieczeństwa | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-msz` | Ministerstwo Spraw Zagranicznych | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-paa` | Państwowa Agencja Atomistyki | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-mswia` | Ministerstwo Spraw Wewnętrznych i Administracji | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-mon` | Ministerstwo Obrony Narodowej | urzędowe | 1 | pełny tekst | 28 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-sluzby-specjalne` | Ministerstwo Koordynator Służb Specjalnych | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-psp` | Komenda Główna Państwowej Straży Pożarnej | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-infrastruktura` | Ministerstwo Infrastruktury | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-gis` | Główny Inspektorat Sanitarny | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-zdrowie` | Ministerstwo Zdrowia | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-cyfryzacja` | Ministerstwo Cyfryzacji | urzędowe | 1 | pełny tekst | 20 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `govpl-klimat` | Ministerstwo Klimatu i Środowiska | urzędowe | 1 | pełny tekst | 10 | CC BY-SA 4.0 (https://www.gov.pl/web/gov/regulamin) |
| `policja` | Komenda Główna Policji | urzędowe | 1 | tytuł + lead + link | 10 | informacja publiczna; brak jawnej licencji na treść - przechowujemy tylko tytuł, datę i link |
| `cert-polska` | CERT Polska (NASK) | urzędowe | 1 | tytuł + lead + link | 100 | brak jawnej licencji na treść - przechowujemy tytuł, lead z RSS i link |
| `ec-presscorner` | Komisja Europejska | urzędowe | 1 | tytuł + lead + link | 10 | CC BY 4.0 - decyzja Komisji 2011/833/UE (https://commission.europa.eu/legal-notice_pl) |
| `ecdc` | Europejskie Centrum ds. Zapobiegania i Kontroli Chorób (ECDC) | urzędowe | 1 | tytuł + lead + link | 10 | CC BY 4.0 (https://www.ecdc.europa.eu/en/copyright) |
| `who` | Światowa Organizacja Zdrowia (WHO) | urzędowe | 1 | tytuł + lead + link | 83 | brak jawnej licencji na treść stron - przechowujemy tytuł, lead z RSS i link (https://www.who.int/about/policies/publishing/copyright) |
| `imgw-synop` | Instytut Meteorologii i Gospodarki Wodnej - PIB | pomiary | 1 | rekord danych | 62 | dane publiczne do ponownego wykorzystania, wymagane podanie źródła "IMGW-PIB" (https://danepubliczne.imgw.pl/) |
| `gios-aq` | Główny Inspektorat Ochrony Środowiska | pomiary | 1 | rekord danych | 13 | dane publiczne Państwowego Monitoringu Środowiska, z podaniem źródła "GIOŚ" (https://powietrze.gios.gov.pl/) |
| `nbp-kursy` | Narodowy Bank Polski | pomiary | 1 | rekord danych | 32 | kursy walut to dane urzędowe, nie utwór; publiczne API NBP (https://api.nbp.pl/) |
| `sejm-eli` | Kancelaria Sejmu - Dziennik Ustaw (ELI API) | akty prawne | 1 | metadane | 60 | akty normatywne nie są przedmiotem prawa autorskiego (art. 4 ustawy o prawie autorskim) |
| `pravda` | Stowarzyszenie Pravda (sygnatariusz IFCN, członek EFCSN) | fact-checking | 2 | tytuł + lead + link | 20 | brak jawnej licencji na treść - przechowujemy tytuł, lead z RSS i link |
| `fakenews-pl` | FakeNews.pl - Fundacja "Przeciwdziałamy Dezinformacji" (sygnatariusz IFCN) | fact-checking | 2 | tytuł + lead + link | 10 | © fakenews.pl - przechowujemy tylko tytuł, lead z RSS i link |
| `cedmo` | CEDMO - Central European Digital Media Observatory (hub EDMO) | fact-checking | 2 | tytuł + lead + link | 10 | brak jawnej licencji na treść - przechowujemy tytuł, lead z RSS i link |

## Źródła wykluczone z pobierania (tylko „sprawdź sam”)

| id | Wydawca | Powód |
|---|---|---|
| `consilium` | Rada Unii Europejskiej | robots.txt zwraca 403 - nie da się sprawdzić zgody na pobieranie, więc ostrożnie nie pobieramy |
| `euvsdisinfo` | EUvsDisinfo (East StratCom Task Force, ESDZ) | robots.txt zabrania pobierania kanałów RSS (Disallow */feed/) - tylko link "sprawdź sam"; dostęp do bazy przez serwer MCP po uzgodnieniu z zespołem EUvsDisinfo |
| `demagog` | Stowarzyszenie Demagog (sygnatariusz IFCN, członek EFCSN) | serwis blokuje automatyczne pobieranie (HTTP 403); nie obchodzimy zabezpieczeń - tylko link "sprawdź sam" |
| `afp-sprawdzam` | AFP Sprawdzam (członek EFCSN) | serwis blokuje automatyczne pobieranie (HTTP 403); nie obchodzimy zabezpieczeń - tylko link "sprawdź sam" |
| `konkret24` | Konkret24 (TVN24) | brak licencji na wykorzystanie treści - tylko link "sprawdź sam" |

## Ograniczenia

- **Krótkie wpisy:** źródła bez jawnej licencji (CERT Polska, WHO, Policja, Pravda, FakeNews.pl, CEDMO) mają w korpusie tylko tytuł, lead i link. Dowód z nich wymaga otwarcia linku.
- **Kanały blokowane:** dwie największe polskie organizacje fact-checkingowe blokują automaty (Demagog, AFP Sprawdzam), a Konkret24 wymaga licencji. Ich wyniki mogą trafiać do systemu przez Google Fact Check Tools API (wymaga klucza), które zbiera oznaczenia ClaimReview.
- **Domena a host:** filtr w `app_simple` porównuje dokładny host. Cytat z innej subdomeny tego samego wydawcy (np. `ecdc.europa.eu` zamiast `www.ecdc.europa.eu`) zostanie odrzucony.

## Serwisy gov.pl (lista dla skilla)

[`config/govpl_whitelist.json`](../config/govpl_whitelist.json) zawiera wszystkie serwisy instytucji na www.gov.pl. Jeden wpis to jeden serwis (`https://www.gov.pl/web/<jednostka>`) i obejmuje wszystkie jego podstrony. Każdy wpis ma pola:
- `linkDoStrony`,
- `krótkiOpisZawartości` (nazwa jednostki, działalność, sekcje serwisu),
- `tagi` (kategoria z katalogu gov.pl i tematy),
- `licencja`.

Źródło spisu: katalog jednostek gov.pl oraz serwisy, do których linkują strony jednostek (np. stacje powiatowe, komendy PSP). Adresy, które przekierowują na stronę główną gov.pl (nieistniejące serwisy), są pomijane. Odświeżenie:

```bash
python scripts/govpl_sites.py
```

Przebieg trwa ok. 20 minut, z przerwą 0,5 s między zapytaniami do gov.pl.
