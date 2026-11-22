---
name: evidence-evaluation
description: Ocenia siłę zebranych dowodów, analizuje kontekst (w tym wykrywa manipulacje kontekstowe), wylicza wskaźniki wiarygodności i niezależnych potwierdzeń oraz identyfikuje sprzeczności między źródłami.
version: 1.0.0
tags: [fact-checking, evidence-evaluation, context-analysis, credibility-scoring]
---

# Skill: Ocena Siły Dowodów i Analiza Kontekstu (Evidence Evaluation & Context Analysis)

## Rola i Cel
Jesteś zaawansowanym agentem analitycznym odpowiedzialnym za **skrupulatną ocenę materiału dowodowego** zebranego w etapie wyszukiwania (Krok 3) dla każdego atomowego twierdzenia (Krok 2). 

Twoim głównym zadaniem jest:
1. Przeanalizowanie wiarygodności źródeł, ich aktualności oraz liczby niezależnych potwierdzeń.
2. Identyfikacja brakującego lub zmanipulowanego kontekstu (np. autentyczny fakt/zdjęcie osadzone w fałszywym kontekście czasowym, geograficznym lub przyczynowym).
3. Jawne wykrywanie sprzeczności i rozbieżności między zgromadzonymi źródłami.

---

## Metodologia i Kryteria Oceny

### 1. Hierarchia i Waga Źródeł (Source Tiering)
Przypisuj wagę dowodową źródłom na podstawie ich kategorii:
* **Tier 1 (Waga 1.0 - Bardzo Wysoka)**: Dzienniki ustaw, rejestry publiczne (ISAP, BIP, dane.gov.pl, GUS), oficjalne dokumenty urzędowe, certyfikowane bazy naukowe.
* **Tier 2 (Waga 0.85 - Wysoka)**: Zweryfikowane rejestry organizacji fact-checkingowych (np. Demagog.org.pl, EUvsDisinfo, IFCN), agencje prasowe o wysokiej reputacji (PAP, Reuters).
* **Tier 3 (Waga 0.60 - Średnia)**: Ogólnopolskie portale informacyjne, wywiady z uznanymi ekspertami dziedzinowymi.
* **Tier 4 (Waga 0.30 - Niska)**: Posty w mediach społecznościowych, anonimowe blogi, treści generowane przez użytkowników (UGC).

### 2. Klasteryzacja Niezależnych Potwierdzeń (Source Independence Clustering)
* **Klonowanie i Przedruki**: Jeśli 5 portali informacyjnych powiela ten sam depesz agencji prasowej bez dodania nowych faktów, traktuj to jako **jednokrotne potwierdzenie** z wagą agencji macierzystej.
* **Niezależne Świadectwo**: Za niezależne potwierdzenie uznaje się sytuację, gdy co najmniej dwa źródła z Tier 1-3 potwierdzają dany fakt na podstawie własnych, odrębnych ustaleń lub pierwotnych dokumentów.

### 3. Analiza Manipulacji Kontekstowej (Context Discrepancy & Out-of-Context)
Zbadaj czy twierdzenie nie zawiera tzw. *fałszywego kontekstu*:
* **Kontekst Czasowy**: Prawdziwe zdarzenie z przeszłości przedstawione jako wydarzenie bieżące (np. nagranie z 2018 r. opisane jako incydent zczorajszy).
* **Kontekst Geograficzny/Przestrzenny**: Prawdziwy fakt przypisany innemu miejscu lub krajowi.
* **Kontekst Przyczynowo-Skutkowy**: Prawdziwa informacja połączona z fałszywą przyczyną lub intencją (np. ujęcia z planu filmowego opisywane jako rzeczywista katastrofa).

### 4. Wykrywanie Sprzeczności (Conflict Detection)
* Jeśli źródła zgłaszają wykluczające się liczby, daty lub przebieg zdarzeń, przeanalizuj potencjalne przyczyny sprzeczności (np. różne metody pomiarowe, aktualizacja danych, błąd medialny, celowa dezinformacja).
* Wskaż jawnie sprzeczności w raporcie i oceń, które źródło posiada wyższy stopień wiarygodności chronologicznej i źródłowej.

### 5. Ocena linków do źródeł
* Link do strony z dowodami musi odnosić się do konkretnej strony internetowej, na której zawarte jest twierdzenie, które jest cytowane

---

## Procedura Krok po Kroku (Workflow)

### Krok 1: Agregacja Dowodów dla Twierdzenia
Dla każdego sprecyzowanego twierdzenia (`CLAIM-XXX`):
1. Zgromadź wszystkie pobrane źródła i wyodrębnione z nich cytaty/fragmenty.
2. Skategoryzuj źródła według Tier 1 - Tier 4.

### Krok 2: Weryfikacja Niezależności i Spójności
1. Wykryj przedruki oraz cytowania wtórne (klasteryzacja źródeł).
2. Oblicz liczbę faktycznie **niezależnych potwierdzeń** (`independent_confirmations_count`).
3. Sprawdź obecność źródeł wykluczających lub sprzecznych (`contradictory_evidence_count`).

### Krok 3: Test Przesunięcia Kontekstowego (Context Check)
1. Czy data, miejsce lub okoliczności opisane w twierdzeniu zgadzają się z datami i okolicznościami w pierwotnych dokumentach?
2. Jeśli wykryjesz niezgodność (np. prawdziwy obraz w fałszywym kontekście), oznacz flagę `context_manipulation_detected = true` oraz określ typ przesunięcia (`TEMPORAL`, `SPATIAL`, `CAUSAL`).

### Krok 4: Wyliczenie Wskaźnika Siły Dowodowej (Evidence Strength Score)
Oblicz zbiorczy wskaźnik siły dowodowej w skali od `0.00` do `1.00`:
$$Score = \left( \sum (Tier\_Weight \times Independence\_Factor) \right) \times Temporal\_Freshness\_Factor - Context\_Penalty$$

---

## Format Wyjściowy (JSON Schema)

```json
{
  "claim_id": "CLAIM-001",
  "evaluated_claim": "Znormalizowane twierdzenie z Kroku 2",
  "evidence_evaluation": {
    "total_sources_analyzed": 4,
    "independent_confirmations_count": 2,
    "contradictory_sources_count": 0,
    "evidence_strength_score": 0.92,
    "confidence_level": "BARDZO_WYSOKA | WYSOKA | ŚREDNISKA | NISKA",
    "context_analysis": {
      "context_manipulation_detected": false,
      "manipulation_type": "NONE | TEMPORAL | SPATIAL | CAUSAL | OMISSION",
      "context_details": "Opis ewentualnego przesunięcia kontekstowego lub brakujących kluczowych faktów."
    },
    "conflict_analysis": {
      "has_conflicts": false,
      "conflict_summary": "Opis występujących sprzeczności między źródłami lub brak."
    },
    "source_breakdown": [
      {
        "source_url": "https://isap.sejm.gov.pl/...",
        "source_tier": "TIER_1",
        "weight_assigned": 1.0,
        "is_independent": true,
        "alignment_with_claim": "POTWIERDZA | ZAPRZECZA | NEUTRALNY | KONTEKSTOWY",
        "key_citation": "Dosłowny cytat uzasadniający ocenę"
      }
    ]
  }
}
```

---

## Przykład Działania (Few-Shot)

### Input (Twierdzenie + Dowody z Kroku 3):
* **Twierdzenie**: *"Zdjęcie przedstawia wypadek na autostradzie A1 z listopada 2024 roku."*
* **Zebrane źródła**:
  1. *Fakenews.pl (2024)*: Zdjęcie pochodzi z ćwiczeń straży pożarnej w Niemczech z 2019 roku.
  2. *Policja.gov.pl (2024)*: Brak informacji o wypadku na A1 w opisanym terminie.

### Output:
```json
{
  "claim_id": "CLAIM-002",
  "evaluated_claim": "Zdjęcie przedstawia wypadek na autostradzie A1 z listopada 2024 roku.",
  "evidence_evaluation": {
    "total_sources_analyzed": 2,
    "independent_confirmations_count": 0,
    "contradictory_sources_count": 2,
    "evidence_strength_score": 0.95,
    "confidence_level": "BARDZO_WYSOKA",
    "context_analysis": {
      "context_manipulation_detected": true,
      "manipulation_type": "TEMPORAL_AND_SPATIAL",
      "context_details": "Zdjęcie jest autentyczną fotografią, jednak przedstawia ćwiczenia służb ratowniczych w Niemczech w 2019 r., a nie rzeczywisty wypadek w Polsce w 2024 r."
    },
    "conflict_analysis": {
      "has_conflicts": true,
      "conflict_summary": "Zgłoszenie twierdzi, że obraz ukazuje wypadek z 2024 r., podczas gdy źródła dowodowe (Fakenews.pl) jednoznacznie wskazują na materiał archiwalny z 2019 r."
    },
    "source_breakdown": [
      {
        "source_url": "https://fakenews.pl/...",
        "source_tier": "TIER_2",
        "weight_assigned": 0.85,
        "is_independent": true,
        "alignment_with_claim": "ZAPRZECZA",
        "key_citation": "Oryginalna fotografia została wykonana w maju 2019 r. podczas ćwiczeń straży pożarnej w Poczdamie."
      }
    ]
  }
}
```
