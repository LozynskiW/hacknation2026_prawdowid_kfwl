# PRAWDOWID – architektura

## 1. Styl
**Modularny monolit**: jeden artefakt, jedna baza, twarde granice modułów.
- Spring Boot + **Spring Modulith**: pakiet najwyższego poziomu = moduł; test `ApplicationModules.of(PrawdowidApplication.class).verify()` w CI blokuje niedozwolone zależności.
- Ścieżka krytyczna (od zapytania do raportu) jest **synchroniczna** przez publiczne API modułów, sterowana przez orkiestrator.
- Efekty uboczne (audyt, sprawy, powiadomienia) idą przez **zdarzenia** z rejestrem publikacji w bazie.
- PostgreSQL + pgvector (pełnotekst + wektory w jednej bazie), Docker Compose.

## 2. Widok ogólny

```
                    ┌──────────────── Kanały ────────────────┐
                    │   WWW (SPA)     Discord bot   WhatsApp* │   * adapter demo
                    └──────┬──────────────┬────────────┬─────┘
                           │              │            │
┌──────────────────────────▼──────────────▼────────────▼──────────────────────────┐
│ M1 access   REST API · adaptery kanałów · rate limit · sesje rozmów · dostarczenie│
└──────────────────────────┬─────────────────────────────────────▲────────────────┘
                           │ submit(InboundMessage) → checkId     │ PresentationModel
┌──────────────────────────▼─────────────────────────────────────┴────────────────┐
│ verification  (orkiestrator, VerificationContext, pętla, budżet czasu)           │
│                                                                                  │
│   M2 intake ──► M3 preselection ──► M4 retrieval ──► M5 reporting ──► M6 review  │
│                       ▲                                                   │      │
│                       └──────────── RETRY + remarks ──────────────────────┘      │
│                                                                   ACCEPT/ABSTAIN │
│                                                                         ▼        │
│                                                                 M7 presentation  │
└────────┬──────────────────┬────────────────────┬─────────────────────┬──────────┘
         │ read API         │ zdarzenia          │ zdarzenia           │ porty
┌────────▼───────┐  ┌───────▼───────┐  ┌─────────▼────────┐  ┌─────────▼──────────────┐
│ catalog        │  │ audit         │  │ cases            │  │ shared                 │
│ whitelista,    │  │ log przebiegu,│  │ sprawy, klastry, │  │ kontrakty, LlmProvider,│
│ sources.yaml,  │  │ metryki, koszt│  │ powiadomienia,   │  │ Fetcher, FactCheck-    │
│ ingest, korpus │  │ zdarzenia bezp│  │ handoff          │  │ Client, Guard (PII,    │
└────────┬───────┘  └───────────────┘  └──────────────────┘  │ injection, walidacja)  │
         │                                                   └────────────────────────┘
┌────────▼────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL + pgvector: sources · documents · chunks · data_points · checks ·     │
│ claims · evidence · reports · cases · events · conversations                     │
└─────────────────────────────────────────────────────────────────────────────────┘
         ▲
┌────────┴──────────────────────┐      ┌─────────────────────────────────┐
│ Ingest (harmonogram w catalog)│      │ Zewnętrzne: LLM (port),          │
│ whitelista → crawler/API →    │      │ Google Fact Check Tools API,     │
│ snapshot + daty + hash        │      │ Discord API                      │
└───────────────────────────────┘      └─────────────────────────────────┘
```

## 3. Przepływ jednego sprawdzenia

```
M1 access ─► verification.submit() ─► 202 + checkId   (kanał: "Sprawdzam…")
                 │
                 ▼
          M2 intake ─► CheckRequest
                 │      status ≠ OK ─► NEEDS_CLARIFICATION / OUT_OF_SCOPE /
                 │                     TECHNICAL_FAILURE ─► M7 (bez werdyktu)
    ┌──────────► M3 preselection ─► SearchPlan          (tylko twierdzenia do sprawdzenia)
    │            │
    │            ▼
    │     M4 retrieval ─► EvidenceSet                   (korpus + Fact Check API + dane)
    │            │
    │            ▼
    │     M5 reporting ─► VerificationReport (draft)    (werdykt z reguł R0–R6)
    │            │
    │            ▼
    │     M6 review ─┬─ ACCEPT ─────────────────────► M7 presentation ─► M1 (push / poll)
    │                │
    └── RETRY ◄──────┤  remarks[tura][uwagi], tylko odrzucone twierdzenia
                     │
                     └─ ABSTAIN (maxRounds / budżet czasu)
                          ─► "brak wystarczających dowodów" + remarks
                          ─► zdarzenie → cases (rekomendacja / sprawa)
```

Kanały są asynchroniczne: Discord wymaga potwierdzenia interakcji w ≤3 s (odpowiedź odroczona), wynik dosyłany po zakończeniu. WWW: polling `GET /api/v1/checks/{id}` lub SSE.

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
Rekordy Javy w `shared.contract`, JSON Schema w `contracts/`, walidacja na granicy modułu.

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
| `chunks` | fragmenty dokumentu: tekst, `tsvector`, embedding |
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
Dla każdego sprawdzenia: czas etapów, wywołania i tokeny modeli, szacunkowy koszt, błędy wyszukiwania, liczba tur, wstrzymania, eskalacje. Endpoint `/actuator/health` z kontrolą zależności (DB, LLM, Fact Check API). Skrypt raportu kosztu 100 testów i 1000 zapytań.

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
`docker compose up` → aplikacja + PostgreSQL. Seed korpusu: `make seed` (lub zadanie startowe). Testy jury-like: `make eval` → raport mierników. Tryb `frozen-corpus` do odtwarzalnych testów (nagrane odpowiedzi źródeł i Fact Check API).
