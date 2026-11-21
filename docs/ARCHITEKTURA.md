# PRAWDOWID – architektura

## 1. Styl
**Modularny monolit**: jeden artefakt, jedna baza, twarde granice modułów.
- Python 3.12 + **FastAPI** (async). Pakiet najwyższego poziomu w `src/prawdowid/` = moduł.
- Publiczne API modułu = jego `__init__.py` (eksport serwisu i typów). Implementacja w `<moduł>/_internal/`.
- **import-linter** w CI blokuje niedozwolone zależności (zakaz importu `_internal` innych modułów, niezależność M2–M6, `shared` bez zależności).
- Kontrakty między modułami: modele **Pydantic v2**; JSON Schema generowana z modeli (`model_json_schema()`) do `contracts/`.
- Ścieżka krytyczna (od zapytania do raportu) wywoływana przez orkiestrator: `await` na publicznych serwisach modułów; równoległość per twierdzenie przez `asyncio.gather` z semaforem.
- Efekty uboczne (audyt, sprawy, powiadomienia) przez **wewnętrzną szynę zdarzeń** (`shared.events`, publish/subscribe w procesie) + tabela `outbox` w bazie, żeby zdarzenie nie zginęło przy błędzie.
- PostgreSQL + pgvector (pełnotekst + wektory w jednej bazie), SQLAlchemy 2 (async) + Alembic, Docker Compose.
- Bot Discord działa jako **osobny proces** (`python -m prawdowid.access.channels.discord`) i woła to samo REST API co WWW – gwarancja tej samej logiki.

## 2. Łańcuch modułów

Każdy moduł to osobny blok. Dane płyną w dół, jeden kontrakt JSON między blokami.

```
┌──────────────────────────────────────┐
│ M1  ACCESS                           │
│ WWW / Discord / WhatsApp (demo)      │
└──────────────────┬───────────────────┘
                   │ InboundMessage
                   ▼
┌──────────────────────────────────────┐
│ M2  INTAKE                           │
│ standaryzacja, PII, twierdzenia      │
└──────────────────┬───────────────────┘
                   │ CheckRequest
                   ▼
┌──────────────────────────────────────┐
│ M3  PRESELECTION                     │◄─────────┐
│ whitelista, zakres dat, zapytania    │          │
└──────────────────┬───────────────────┘          │
                   │ SearchPlan                   │
                   ▼                              │
┌──────────────────────────────────────┐          │
│ M4  RETRIEVAL                        │          │
│ korpus, Fact Check API, cytaty       │          │
└──────────────────┬───────────────────┘          │
                   │ EvidenceSet                  │ RETRY
                   ▼                              │ + remarks
┌──────────────────────────────────────┐          │ (maks. 2 tury)
│ M5  REPORTING                        │          │
│ werdykt z reguł, wstępny raport      │          │
└──────────────────┬───────────────────┘          │
                   │ VerificationReport           │
                   ▼                              │
┌──────────────────────────────────────┐          │
│ M6  REVIEW                           │──────────┘
│ kontrola cytatów i ugruntowania      │
└──────────────────┬───────────────────┘
                   │ ACCEPT / ABSTAIN
                   ▼
┌──────────────────────────────────────┐
│ M7  PRESENTATION                     │
│ raport czytelny dla obywatela        │
└──────────────────┬───────────────────┘
                   │ PresentationModel
                   ▼
              M1 → użytkownik
```

## 3. Moduły wspierające

Nie są ogniwami łańcucha. Łańcuch z nich korzysta.

```
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ VERIFICATION       │  │ CATALOG            │  │ SHARED             │
│ uruchamia łańcuch, │  │ whitelista,        │  │ kontrakty, LLM,    │
│ pętla, limit czasu │  │ korpus, ingest     │  │ Fetcher, Guard     │
└────────────────────┘  └────────────────────┘  └────────────────────┘
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ AUDIT              │  │ CASES              │  │ POSTGRESQL         │
│ log, metryki,      │  │ sprawy moderatora, │  │ + pgvector         │
│ koszt              │  │ powiadomienia      │  │                    │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

| Kto | Z czego korzysta |
|---|---|
| M3, M4 | CATALOG |
| M2, M4, M5, M6 | SHARED (LLM, Fetcher, Guard) |
| wszystkie | AUDIT, CASES (przez zdarzenia) |

Uwagi do przebiegu:
- M2 może zakończyć łańcuch od razu (doprecyzowanie, poza zakresem, awaria). Wtedy wynik idzie prosto do M7, bez werdyktu.
- Kanał dostaje natychmiast „Sprawdzam…”, wynik przychodzi po zakończeniu łańcucha.

## 4. Reguły zależności

```
access        ──► verification (submit, getResult), presentation
verification  ──► intake, preselection, retrieval, reporting, review, presentation
preselection  ──► catalog (read)
retrieval     ──► catalog (read), shared (FactCheckClient, Fetcher, LlmProvider)
intake        ──► shared (Fetcher, Guard, LlmProvider)
reporting     ──► shared (konfiguracja reguł)
review        ──► shared (LlmProvider), reporting (VerdictRules – ponowne przeliczenie)
wszystkie     ──(zdarzenia)──► audit, cases
```
- M2–M6 **nie wołają się nawzajem**. Wyjątek: `review` używa publicznego `VerdictRules` z `reporting` do przeliczenia.
- `shared` nie zależy od żadnego modułu.
- Adaptery kanałów nie zawierają logiki merytorycznej.

Konfiguracja import-linter (`.importlinter`, szkic):
```ini
[importlinter]
root_package = prawdowid

[importlinter:contract:no-internal]
name = Zakaz importu _internal innych modułów
type = forbidden
source_modules = prawdowid.intake prawdowid.preselection prawdowid.retrieval prawdowid.reporting prawdowid.review prawdowid.presentation prawdowid.verification prawdowid.access
forbidden_modules = prawdowid.catalog._internal prawdowid.cases._internal prawdowid.audit._internal
# (analogicznie dla każdego modułu)

[importlinter:contract:pipeline-independent]
name = Moduły pipeline niezależne od siebie
type = independence
modules = prawdowid.intake prawdowid.preselection prawdowid.retrieval prawdowid.presentation
# reporting/review: wyjątek review -> reporting (VerdictRules), osobny kontrakt forbidden

[importlinter:contract:shared-leaf]
name = shared nie zależy od modułów
type = forbidden
source_modules = prawdowid.shared
forbidden_modules = prawdowid.access prawdowid.intake prawdowid.preselection prawdowid.retrieval prawdowid.reporting prawdowid.review prawdowid.presentation prawdowid.verification prawdowid.catalog prawdowid.cases prawdowid.audit
```

## 5. Pętla ponownej weryfikacji
- M6 mierzy **ugruntowanie** raportu (`groundingScore`), nie „prawdę”.
- Do M3 wracają tylko twierdzenia poniżej progu; zaakceptowane są zamrożone.
- `maxRounds = 2`, budżet czasu 25 s. Po wyczerpaniu: degradacja do „brak wystarczających dowodów”.
- Powtórka zmienia **sposób szukania** (zakres dat, typy źródeł, język, przeformułowanie, wykluczenie fragmentów), nie oczekiwany wynik.
- Uwagi: `remarks` = lista list. Indeks zewnętrzny = tura, lista wewnętrzna = uwagi z tury. Brak powtórek → `[]`.

```json
"remarks": [
  [ { "claimId": "c1", "code": "QUOTE_NOT_FOUND", "chunkId": "ch_8812",
      "message": "Cytat nie występuje w fragmencie źródła", "action": "DROP_CHUNK" },
    { "claimId": "c1", "code": "STALE_SOURCE", "message": "Najnowsze źródło z 2021 r.",
      "action": "WIDEN_DATE_RANGE", "params": { "from": "2025-01-01" } } ],
  [ { "claimId": "c1", "code": "NO_EVIDENCE_AFTER_RETRY",
      "message": "Po rozszerzeniu zakresu brak źródeł", "action": "ABSTAIN" } ]
]
```

Szczegóły reguł werdyktu i progów M6: `docs/MODULY.md` (sekcje M5 i M6).

## 6. Kontrakty (JSON, `schemaVersion: "1.0"`)
Modele Pydantic w `prawdowid/shared/contracts/`, JSON Schema generowana do `contracts/` (`make schemas`), walidacja przy każdym przejściu między modułami i przy każdej odpowiedzi LLM.

| Kontrakt | Producent → konsument | Kluczowe pola |
|---|---|---|
| `InboundMessage` | M1 → verification | `channel`, `conversationId`, `text`, `url`, `receivedAt` |
| `CheckRequest` | M2 → M3 | `checkId`, `input{type,rawTextMasked,url,fetch}`, `claims[]{claimId,text,type,checkworthy,entities,timeRef,place,topic}`, `flags`, `status` |
| `SearchPlan` | M3 → M4 | `round`, `claims[]{claimId,queries,sourceTypes,hosts,dateRange,languages,excludeChunks}` |
| `EvidenceSet` | M4 → M5 | `evidence[]{claimId,type,chunkId/dataPointId/reviewUrl,source{title,publisher,url,publishedAt,fetchedAt,validFrom,validTo,observedAt,tier},quote/value,stance,match,relevance}`, `searchErrors[]` |
| `VerificationReport` | M5 → M6 → M7 | `claims[]{outcome{kind,verdict},strength{level,factors},explanation,evidenceIds,warnings,unknowns,groundingScore}`, `review`, `remarks`, `handoff`, `metrics`, `corpusVersion`, `pipelineVersion` |
| `PresentationModel` | M7 → M1 | etykiety PL, karty twierdzeń, karty źródeł, ostrzeżenia, „czego nie ustalono”, link do pełnego wyniku |

Słowniki:
- `outcome.kind`: `VERDICT | NOT_CHECKABLE | NEEDS_CLARIFICATION | OUT_OF_SCOPE | TECHNICAL_FAILURE | CANNOT_CHECK`
- `verdict`: `CONFIRMED | FALSE | MISLEADING | INSUFFICIENT_EVIDENCE`
- `evidence.type`: `QUOTE | DATA_POINT | FACT_CHECK_REVIEW`
- `handoff.status`: `NONE | RECOMMENDED | CASE_CREATED`

## 7. Dane (tabele)
| Tabela | Zawartość |
|---|---|
| `sources` | wpis whitelisty/katalogu: URL, host, typ, tier, rola (`EVIDENCE`/`REFERRAL`), metoda pobrania, częstotliwość, licencja, status, powód wykluczenia |
| `documents` | snapshot: URL kanoniczny, tytuł, wydawca, `published_at`, `fetched_at`, `valid_from/to`, hash, flaga injection |
| `chunks` | fragmenty dokumentu: tekst, `tsvector`, embedding (`vector(768)` lub zgodnie z modelem) |
| `data_points` | pomiary: wartość, jednostka, stacja/obszar, `observed_at`, źródło |
| `checks` | zgłoszenie: kanał, zamaskowany tekst, czasy etapów, tokeny, koszt, wersje, status, `expires_at` |
| `claims`, `evidence`, `reports` | wynik per sprawdzenie (JSONB + kolumny do raportowania) |
| `cases` | sprawy moderatora, klaster podobnych zgłoszeń, status, odbiorca |
| `events` | audyt i bezpieczeństwo: `InjectionDetected`, `Abstained`, błędy wyszukiwania |
| `conversations` | stan rozmowy kanału (doprecyzowanie) z TTL |

## 8. Bezpieczeństwo i prywatność (przekrojowo)
- **Wejście:** limit rozmiaru, walidacja URL (tylko http/https), rate limit per kanał i użytkownik.
- **Fetcher:** ochrona SSRF (blokada adresów prywatnych i link-local, kontrola przekierowań), timeout, limit rozmiaru, robots.txt, czytelny User-Agent, brak omijania zabezpieczeń.
- **LLM:** instrukcje systemowe oddzielone od danych, treści w oznaczonych polach, brak narzędzi dla modeli czytających treść, wyjście tylko JSON według schematu (niepoprawny → 1 ponowienie → `TECHNICAL_FAILURE`).
- **Injection:** detektor heurystyczny + flaga dokumentu + zdarzenie; werdykt liczony kodem.
- **PII:** maskowanie (PESEL, telefon, e-mail, adres, imię i nazwisko osób prywatnych) przed LLM i przed zapisem; retencja `checks` 30 dni (konfigurowalne), `DELETE /api/v1/sessions/{id}`.
- **Sekrety:** zmienne środowiskowe, `.env.example`, skan sekretów w CI.
- **Odporność:** timeouty, circuit breaker na LLM i Fact Check API, kolejka z limitem równoległości (backpressure), komunikat „spróbuj za chwilę”.

## 9. Obserwowalność
Dla każdego sprawdzenia: czas etapów, wywołania i tokeny modeli, szacunkowy koszt, błędy wyszukiwania, liczba tur, wstrzymania, eskalacje. Endpoint `GET /health` (żywotność) i `GET /health/ready` (DB, LLM, Fact Check API). Logi strukturalne JSON (`structlog`), opcjonalnie metryki Prometheus. Skrypt raportu kosztu 100 testów i 1000 zapytań.

## 10. Budżet czasu (cel: mediana ≤ 30 s)
| Etap | Szacunek |
|---|---|
| M2 (pobranie URL + ekstrakcja) | 2–4 s |
| M3 | < 0,5 s |
| M4 (równolegle per twierdzenie) | 4–8 s |
| M5 | 2–3 s |
| M6 | 2–3 s |
| Tura 1 | ~12–18 s |
| Tura 2 (tylko odrzucone) | +8–12 s |

## 11. Uruchomienie
`docker compose up` → `api` (FastAPI/uvicorn), `discord-bot`, `db` (PostgreSQL + pgvector), opcjonalnie `worker` (ingest wg harmonogramu).
- Migracje: `alembic upgrade head` (przy starcie kontenera).
- Seed korpusu: `make seed` (`python -m prawdowid.catalog.ingest`).
- Testy: `make test` (pytest + import-linter), `make eval` → raport mierników.
- Tryb `FROZEN_CORPUS=1` do odtwarzalnych testów (nagrane odpowiedzi źródeł i Fact Check API).

## 12. Wybór bibliotek (do weryfikacji licencji – kod przechodzi na MSZ, unikamy copyleftu)
| Obszar | Biblioteka |
|---|---|
| API | FastAPI, uvicorn, pydantic v2, pydantic-settings |
| Baza | SQLAlchemy 2 (async), asyncpg, Alembic, pgvector (python) |
| HTTP / pobieranie | httpx (timeouty, limity), własna ochrona SSRF |
| Ekstrakcja treści HTML | trafilatura lub readability-lxml (**sprawdzić licencję wybranej wersji**) |
| Embeddingi | sentence-transformers + model wielojęzyczny (np. rodzina multilingual-e5), lokalnie |
| PII | reguły regex PL (PESEL, NIP, telefon, e-mail, IBAN) + opcjonalnie Presidio |
| Rate limit | slowapi |
| Odporność | tenacity (ponowienia), prosty circuit breaker |
| Discord | discord.py |
| WWW | Jinja2 + HTMX (serwowane przez FastAPI) – najmniej kodu, bez osobnego builda |
| Testy / jakość | pytest, pytest-asyncio, respx (mock HTTP), import-linter, ruff, mypy |
| Pakiety | uv |

Uwaga: wbudowane konfiguracje wyszukiwania pełnotekstowego PostgreSQL **nie mają języka polskiego**. Opcje: słownik `simple` + `unaccent` (najprościej), albo doinstalowanie słownika polskiego (hunspell/ispell) w obrazie Dockera. Wyszukiwanie wektorowe kompensuje brak stemmingu.
