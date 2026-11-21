# PRAWDOWID – opis projektu

> Zadanie MSZ w ramach HackNation 2026. Prototyp end-to-end budowany w 24 h.

## Cel
Obywatel sprawdza pogłoskę lub doniesienie tak łatwo, jak wysyła wiadomość. Wkleja tekst albo link (WWW lub Discord), a system:
1. wyodrębnia twierdzenia warte sprawdzenia,
2. szuka dowodów wyłącznie w jawnym, audytowalnym zbiorze źródeł,
3. zwraca werdykt dla każdego twierdzenia z uzasadnieniem, cytatami i oceną siły dowodów,
4. uczciwie wstrzymuje się od rozstrzygnięcia, gdy dowodów brakuje.

System **wspiera** ocenę informacji i pokazuje dowody. Nie jest automatycznym „sędzią prawdy”.

## Odbiorcy
- **Obywatel** – także osoba o niskich kompetencjach cyfrowych. Prosty polski, bez żargonu, bez instalacji, bezpłatnie.
- **Administrator / moderator / analityk** – log sprawdzeń, sprawy dla nierozstrzygniętych zgłoszeń, powiadomienia o sprawach wysokiego ryzyka i powtarzających się pytaniach bez odpowiedzi.

## Wynik dla twierdzenia
| Rodzaj | Wartości |
|---|---|
| Werdykt | potwierdzone · fałszywe · wprowadzające w błąd · brak wystarczających dowodów · nie podlega weryfikacji |
| Status (to **nie** jest werdykt) | potrzeba doprecyzowania · poza zakresem · awaria techniczna · brak możliwości sprawdzenia |

Każde źródło: tytuł, wydawca, data publikacji, data pobrania, link, wykorzystany fragment lub wartość pomiaru.

## Źródła
1. **Whitelista urzędowa (40 URL, 18 hostów)** – bezpieczeństwo i ochrona ludności: RCB, MSWiA, gov.pl/ostrzeżenia, IMGW (meteo, hydro, Bałtyk), PAA (promieniowanie), GIOŚ (powietrze), GIS, GDDKiA, ULC, UTK, Portal Pasażera, SOK, SAR, urzędy morskie, Wody Polskie, CERT, Policja, PSP, MON, MSZ (podróże), Odyseusz, Premier, Ministerstwo Infrastruktury.
2. **Google Fact Check Tools API** – oceny fact-checkerów (ClaimReview).

Plik źródłowy: `config/whitelist.txt`, katalog z metadanymi: `config/sources.yaml`.

## Twarde zasady
- Żadna teza nie jest podana jako ustalenie bez dowodu ze źródła.
- Werdykt liczą **reguły w kodzie**, nie model językowy. LLM rozumie pytanie, ocenia fragmenty i pisze wyjaśnienie.
- Domena, autor, popularność, status źródła (np. sankcje) ani dopasowanie do znanego incydentu **nie przesądzają** o werdykcie. Mogą wywołać tylko neutralne ostrzeżenie.
- Instrukcje znalezione w treściach źródeł i w zapytaniach użytkownika nie zmieniają działania systemu (ochrona przed prompt injection).
- Awaria, brak klucza API i limit nigdy nie są przedstawiane jako wynik merytoryczny.
- Nie obchodzimy zabezpieczeń serwisów, paywalli ani logowania.
- Dane osobowe maskujemy przed wysłaniem do modeli. Retencja jest określona, a sesję demonstracyjną da się usunąć.
- Sekrety i klucze API nigdy nie trafiają do repozytorium.

## Kanały
- **WWW** – responsywny interfejs (MVP).
- **Discord** – bot korzystający z tego samego API (drugi kanał MVP).
- **WhatsApp** – adapter demonstracyjny / docelowo.

Ten sam input przez dowolny kanał daje ten sam wynik merytoryczny.

## Cele jakościowe (mierniki jury)
| Miernik | Cel |
|---|---|
| Trafność werdyktu (macro-F1) | ≥ 0,75 |
| Pokrycie cytowań | ≥ 95% |
| Poprawność cytowań | ≥ 85% |
| Poprawne wstrzymanie się przy braku dowodów | ≥ 80% |
| Odporność na prompt injection | ≥ 90% |
| Mediana czasu odpowiedzi (tekst/URL) | ≤ 30 s |
| End-to-end bez interwencji / spójność kanałów | 100% |

## Stos technologiczny
Java + Spring Boot, **Spring Modulith** (modularny monolit), PostgreSQL + pgvector, Docker Compose. Modele językowe za wymiennym portem `LlmProvider` (preferencja dostawców z EOG lub self-host).

## Dokumenty
- `docs/ARCHITEKTURA.md` – architektura, przepływ, kontrakty.
- `docs/MODULY.md` – opis modułów i zadań dla zespołu i agentów AI.
