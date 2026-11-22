---
name: google-fact-check
description: Wyszukuje zweryfikowane twierdzenia (ClaimReview) przez Google Fact Check Tools API. Używaj gdy trzeba sprawdzić czy dane twierdzenie było już weryfikowane przez niezależnych fact-checkerów.
version: 1.0.0
tags: [fact-checking, google-api, claim-review, external-verification, api]
---

# Skill: Google Fact Check Tools API

## Rola i Cel
Jesteś agentem wyszukującym istniejące weryfikacje fact-checkingowe (ClaimReview) dla danego twierdzenia przez oficjalne Google Fact Check Tools API. API agreguje oznaczenia ClaimReview publikowane przez zweryfikowanych fact-checkerów na całym świecie.

---

## 1. Endpoint i Uwierzytelnienie

- **Base URL:** `https://factchecktools.googleapis.com`
- **Główna metoda:** `GET /v1alpha1/claims:search`
- **Uwierzytelnienie:** klucz API jako query parameter `key` (pobierz ze zmiennej środowiskowej `GOOGLE_FACT_CHECK_API_KEY`)
- **Dokumentacja:** https://developers.google.com/fact-check/tools/api

---

## 2. Parametry Zapytania

| Parametr | Wymagany | Opis |
|----------|----------|------|
| `query` | TAK | Tekst twierdzenia do wyszukania (max ~512 znaków) |
| `languageCode` | NIE | Kod języka ISO 639-1 (np. `pl` dla polskiego, `en` dla angielskiego) |
| `pageSize` | NIE | Liczba wyników (domyślnie 5, max 10) |
| `offset` | NIE | Przesunięcie dla paginacji (domyślnie 0) |
| `key` | TAK | Klucz API Google Cloud |

---

## 3. Przykład Wywołania

```
GET https://factchecktools.googleapis.com/v1alpha1/claims:search?query=szczepionki%20powoduja%20autyzm&languageCode=pl&pageSize=5&key=GOOGLE_FACT_CHECK_API_KEY
```

---

## 4. Struktura Odpowiedzi (ClaimReview)

API zwraca obiekt `SearchClaimsResponse` zawierający tablicę `claims`:

```json
{
  "claims": [
    {
      "claimReview": [
        {
          "claimText": "Szczepionki powodują autyzm",
          "textualRating": "Fałszywe",
          "publisher": {
            "name": "Demagog.org.pl",
            "site": "demagog.org.pl"
          },
          "url": "https://demagog.org.pl/wypowiedzi/weryfikacje/...",
          "title": "Czy szczepionki powodują autyzm?",
          "reviewDate": "2024-03-15T00:00:00Z",
          "languageCode": "pl"
        }
      ],
      "claimText": "Szczepionki powodują autyzm",
      "claimant": "użytkownik Facebooka"
    }
  ],
  "nextPageToken": "..."
}
```

### Kluczowe pola `ClaimReview`:
- `claimText` — weryfikowane twierdzenie
- `textualRating` — ocena słowna (np. "Prawda", "Fałszywe", "Wprowadza w błąd", "Częściowo prawda")
- `publisher.name` — nazwa organizacji fact-checkingowej
- `publisher.site` — domena fact-checkera
- `url` — link do pełnej weryfikacji
- `title` — tytuł artykułu weryfikacyjnego
- `reviewDate` — data publikacji weryfikacji (ISO 8601)
- `languageCode` — język weryfikacji

---

## 5. Procedura Wyszukiwania

1. **Przygotuj query:**
   - Wyodrębnij z twierdzenia kluczowe encje, liczby, daty i nazwy własne
   - Usuń ozdobniki językowe ("rzekomo", "podobno", "wierzę że")
   - Maksymalna długość: ~512 znaków

2. **Wybierz język:**
   - Dla polskich treści użyj `languageCode=pl`
   - Jeśli nie znajdziesz wyników, spróbuj `languageCode=en`

3. **Wywołaj API:**
   - `pageSize=5` dla zmniejszenia kontekstu

4. **Przeanalizuj wyniki:**
   - Jeśli `claims` jest puste — brak istniejących weryfikacji
   - Dla każdego wyniku zanotuj: `textualRating`, `publisher.name`, `url`, `reviewDate`

---

## 6. Format Wyjściowy (JSON)

```json
{
  "api_status": {
    "called": true,
    "success": true,
    "results_count": 3,
    "language_used": "pl"
  },
  "query_used": "szczepionki powodują autyzm",
  "fact_check_results": [
    {
      "claim_text": "Szczepionki powodują autyzm",
      "textual_rating": "Fałszywe",
      "rating_normalized": "FALSE",
      "publisher_name": "Demagog.org.pl",
      "publisher_site": "demagog.org.pl",
      "verification_url": "https://demagog.org.pl/...",
      "verification_title": "Czy szczepionki powodują autyzm?",
      "review_date": "2024-03-15",
      "language": "pl",
      "source_type": "google_fact_check"
    }
  ],
  "summary": "Znaleziono 3 weryfikacje tego twierdzenia przez akredytowanych fact-checkerów. Wszystkie oceniają je jako fałszywe."
}
```

### Normalizacja ocen (`rating_normalized`):
| `textualRating` (przykład) | `rating_normalized` |
|---------------------------|---------------------|
| "Prawda", "True", "Correct" | `TRUE` |
| "Fałszywe", "False", "Pants on Fire" | `FALSE` |
| "Wprowadza w błąd", "Mostly false", "Misleading" | `MISLEADING` |
| "Częściowo prawda", "Half true", "Mixture" | `MIXTURE` |
| "Brak dowodów", "Unproven", "Needs more evidence" | `UNPROVEN` |
| Inne | `OTHER` |

---

## 7. Obsługa Błędów

- **Brak klucza API:** zwróć `api_status.success: false` z komunikatem o braku `GOOGLE_FACT_CHECK_API_KEY`
- **HTTP 403:** klucz nieprawidłowy lub API niedostępne dla projektu
- **HTTP 429:** przekroczono limit zapytań — zwróć informację o rate limit
- **Pusta odpowiedź (`claims: []`):** brak istniejących weryfikacji — to NIE oznacza, że twierdzenie jest prawdziwe
- **Timeout/błąd sieci:** zwróć `api_status.success: false` i kontynuuj z innymi źródłami

---

## 8. Zasady Bezpieczeństwa

- **Nigdy nie wysyłaj danych osobowych** użytkownika do API (anonimizuj query)
- **Nie traktuj wyniku API jako ostatecznego werdyktu** — to tylko jedna z przesłanek
- **Zawsze cytuj źródło:** podawaj `publisher.name` i `url` przy każdym wyniku
- **Sprawdzaj datę:** `reviewDate` — weryfikacja sprzed lat może być nieaktualna
