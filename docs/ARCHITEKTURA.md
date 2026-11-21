# PRAWDOWID – architektura

## 1. Ogólnie
Aplikacja to zbiór endpointów posegregowanych na tematyczne moduły. Interakcje z API wykonuje wyspecjalizowany agent AI. Zbiór endpoitów jest zaimplementowany jako modularny monolit.

## 1. Zasady
- jedna baza danych
- jedna funkcjonalność to jeden moduł
- moduły dzielimy na główne i util
- każdy moduł główny ma własne API z jednym endpointem - definiuje jeden obiekt, który przyjmuje i zwraca jeden obiekt
- moduły util można dowolnie wykorzystać w innych modułach
- język: Python 3.12 + **FastAPI** (async)

## 2. Moduły główne

Każdy moduł to osobny blok. Dane płyną w dół, jeden kontrakt JSON między blokami.

```
┌──────────────────────────────────────┐
│ M1  ACCESS                           │
│ interfejs WWW / komunikator          │
└──────────────────┬───────────────────┘
                   │ InboundMessage
                   ▼
┌──────────────────────────────────────┐
│ M2  INTAKE                           │
│ standaryzacja, tworzenie tagów       │
└──────────────────┬───────────────────┘
                   │ CheckRequest
                   ▼
┌──────────────────────────────────────┐
│ M3  PRESELECTION                     │◄─────────┐
│ ograniczenie zakresu wyszukiwania    │          │
└──────────────────┬───────────────────┘          │
                   │ SearchPlan                   │
                   ▼                              │
┌────────────────────────────────────────┐          │
│ M4  RETRIEVAL                          │          │
│ wyszukiwanie danych ze stron przez URL │          │
└──────────────────┬─────────────────────┘          │
                   │ EvidenceSet                  │ RETRY
                   ▼                              │ + remarks
┌──────────────────────────────────────┐          │ (maks. 2 tury)
│ M5  REPORTING                        │          │
│ werdykt z reguł, wstępny raport      │          │
└──────────────────┬───────────────────┘          │
                   │ VerificationReport           │
                   ▼                              │
┌──────────────────────────────────────────────────────────────────┐          │
│ M6  REVIEW                                                       │──────────┘
│ kontrola raportu - fakty + zgodność z żądaniem użytkownika       │
└──────────────────┬───────────────────────────────────────────────┘
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
AI_AGENT - api do AI providera
AUDIT - log, metryki, koszt
POSTGRESQL - dostęp do bazy
```
