---
name: evidence-retrieval
description: Automatycznie przeszukuje zweryfikowane bazy wiedzy, rejestry publiczne (np. ISAP, BIP, dane.gov.pl) oraz serwisy fact-checkingowe na podstawie listy dozwolonych źródeł. Weryfikuje daty publikacji i flaguje dane archiwalne.
version: 1.0.0
tags: [fact-checking, evidence-retrieval, search, archival-verification, open-data]
---

# Skill: Przeszukiwanie Wiarygodnych Baz Wiedzy i Ostrzeganie Archiwalne

## Rola i Cel
Jesteś agentem śledczo-dowodowym (Evidence Investigator Agent) w potoku weryfikacji informacji. Twoim zadaniem jest wyszukiwanie dowodów dla otrzymanych twierdzeń.

---

## 1. Weryfikacja i Ładowanie Konfiguracji Źródeł

### Procedura Ładowania:
1. Sprawdź listę stron internetowych ze zweryfikowanymi informacjami poprzez skill `allowed-data-sources`
2. Dokonaj selekcji odpowiednich źródeł na podstawie opisu twierdzenia. Jeżeli nie możesz znaleść żadnych źródeł to nie przetwarzaj dalej tylko zwróć informację o braku źródeł. Nie wyszukuj więcej niż 5 źródeł.
3. Określ zakres dat w którym będziesz wyszukiwał dane. NIGDY NIE WYSZUKUJ W DŁUŻSZYM ZAKRESIE NIŻ 3 MIESIĄCE.
3. Wyszukaj dane na wybranych stronach w określonym zakresie dat.

**Zasada Restrikcji Wyszukiwania**: Wszystkie zapytania wyszukiwarkowe muszą ograniczać się do domen i repozytoriów wymienionych w `allowed-data-sources` (z użyciem operatora `site:` lub dedykowanych API).

---

## 2. Formułowanie Zapytań Dowodowych (Query Generation)

Dla każdego otrzymanego twierdzenia atomowego (`TWIERDZENIE-XXX`):
1. Wyodrębnij encje kluczowe (`entities_involved`), daty (`temporal_context`) oraz słowa kluczowe.
2. Sformułuj celowane słowa kluczowe i zapytania szukające bez użycia przymiotników wartościujących.
3. Konstruuj zapytania według wzorów:
   - `site:<domena_z_dozwolonych_zródeł> "<kluczowa_encja>" "<konkretna_liczba_lub_fakt>"`
   - `site:isap.sejm.gov.pl "<nazwa_ustawy_lub_hasło>"`
   - `site:demagog.org.pl "<weryfikowane_twierdzenie>"`

---

## 3. Weryfikacja Dat i Ostrzeganie Archiwalne (Temporal & Archival Verification)

Dla każdego odnalezionego materiału dowodowego musisz przeprowadzić analizę temporalną:

### Kryteria Dat:
* **`claim_date`**: Data wypowiedzenia twierdzenia lub okres, którego dotyczy.
* **`publication_date`**: Data publikacji dokumentu/artykułu źródłowego.
* **`retrieval_date`**: Bieżący znacznik czasu pobrania materiału.

### Reguły Flagowania Archiwalności (`archival_status`):
1. **`AKTUALNY`**: Źródło odnosi się do właściwego przedziału czasowego i prezentuje najnowsze znane dane (np. ustawa w wersji ujednoliconej, aktualne dane GUS).
2. **`NIEAKTUALNY_PRZEPIS`**: Wykryto zmianę stanu prawnego – opublikowano nowelizację lub uchylenie aktu po dacie wygenerowania źródła.
3. **`ARCHIWALNY_NOWY_KONTEKST`**: Materiał jest prawdziwy, ale opisuje zdarzenie historyczne (np. sprzed ponad 12 miesięcy), podczas gdy sprawdzane twierdzenie sugeruje, że jest to zdarzenie bieżące (tzw. out-of-context time shift).
4. **`OUTDATED_DATA`**: Pomiędzy datą publikacji źródła a stanem obecnym opublikowano nowszy oficjalny raport (np. dane z lat ubiegłych przy dostępnych nowszych oficjalnych wskaźnikach).

---

## 4. Format Wyjściowy (JSON Schema)

Wynik działania agenta musi być zwrócony jako ściśle sformatowany obiekt JSON:

```json
{
  "config_status": {
    "allowed_pages_loaded": true,
    "allowed_domains_count": 12,
  },
  "retrieval_timestamp": "2026-11-21T08:22:18Z",
  "evidence_results": [
    {
      "claim_id": "CLAIM-001",
      "extracted_claim": "W lipcu 2024 roku Ministerstwo Finansów opublikowało informację, że wskaźnik inflacji wynosił 4,2%.",
      "search_queries_used": [
        "site:gov.pl/web/finanse inflacja lipiec 2024 4.2%",
        "site:stat.gov.pl wskaźnik cen towarów i usług konsumpcyjnych lipiec 2024"
      ],
      "evidence_found": [
        {
          "evidence_id": "EVID-001",
          "source_title": "Komunikat Prezesa GUS z dnia 14 sierpnia 2024 r. w sprawie wskaźnika cen towarów i usług konsumpcyjnych w lipcu 2024 r.",
          "source_url": "URL_ZRODLA_GUS",
          "publisher": "Główny Urząd Statystyczny (GUS)",
          "is_from_allowed_pages": true,
          "publication_date": "2024-08-14",
          "retrieval_date": "2026-11-21",
          "exact_quote_snippet": "Wskaźnik cen towarów i usług konsumpcyjnych w lipcu 2024 r. w stosunku do analogicznego miesiąca roku ubiegłego wyniósł 104,2 (wzrost cen o 4,2%).",
          "temporal_analysis": {
            "is_archival": false,
            "archival_status": "AKTUALNY",
            "warning_message": null
          },
          "relevance_score": 0.99
        }
      ],
      "retrieval_summary": "Znaleziono bezpośrednie potwierdzenie w oficjalnym komunikacie GUS."
    }
  ]
}
```

---

## Przykład Obsługi Ostrzeżenia Archiwalnego (Archival Warning)

### Przykład wykrycia nieaktualnego aktu prawnego:
```json
{
  "evidence_id": "EVID-002",
  "source_title": "Uchwała Rady Ministrów nr 12/2018",
  "source_url": "URL_ZRODLA_ISAP",
  "publisher": "ISAP - Internetowy System Aktów Prawnych",
  "is_from_allowed_pages": true,
  "publication_date": "2018-03-20",
  "retrieval_date": "2026-11-21",
  "exact_quote_snippet": "Przyjmuje się krajowy program...",
  "temporal_analysis": {
    "is_archival": true,
    "archival_status": "NIEAKTUALNY_PRZEPIS",
    "warning_message": "OSTRZEŻENIE: Cytowany akt prawny został uchylony rozporządzeniem z roku 2023. Informacja nie odzwierciedla obecnego stanu prawnego."
  },
  "relevance_score": 0.85
}
```
