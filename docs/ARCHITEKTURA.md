# Architektura Prawdowida

Krótki opis: z czego składa się system, jak płyną dane, jakich modeli i dostawców używamy i czego system nie robi.

## Składniki

```
 Użytkownik
    │
    ├── Strona WWW (HTMX)  ──POST /wynik──┐
    │                                     │
    └── Bot Discorda ──POST /api/v1/check─┤
                                          ▼
                    ┌──────────── Backend (FastAPI) ─────────────┐
                    │ 1. walidacja wejścia i limit zapytań        │
                    │ 2. maskowanie danych osobowych              │
                    │ 3. pytanie do agenta (lokalny OpenCode V2)  │──► dostawca modelu (np. Mistral)
                    │ 4. kontrola źródeł w odpowiedzi             │
                    │ 5. zapis w logu (SQLite) i wynik            │
                    └────────────────────────────────────────────┘
                                          │
                      Agent pobiera strony tylko z listy dozwolonych
                      (gov.pl, IMGW, Policja, CERT, PAP, ... + Google Fact Check API)
```

| Składnik | Technologia | Pliki |
|---|---|---|
| Strona WWW | szablony Jinja2, HTMX, własny CSS/JS (oko) | `src/prawdowid/web/` |
| Bot Discorda | discord.py, komendy `/sprawdz`, `/usun`, `/pomoc`, wiadomości prywatne | `src/prawdowid/discord_bot/` |
| Backend i API | Python 3.12, FastAPI | `src/prawdowid/api/` |
| Agent weryfikujący | OpenCode V2 (otwartoźródłowy) z agentem i 8 skillami | `.opencode/` |
| Log sprawdzeń | SQLite (jeden plik, retencja 7 dni) | `src/prawdowid/api/checklog.py` |
| Uruchomienie | Docker Compose: kontenery `app` i `bot` | `Dockerfile`, `docker-compose.yml` |

Oba kanały korzystają z tej samej funkcji `run_check` w backendzie. Kanał tylko zbiera pytanie i pokazuje wynik, a o werdykcie decyduje wspólna logika.

## Przepływ danych

1. **Wejście.** Użytkownik wkleja tekst lub link na stronie albo pisze do bota. Bot zamienia ID Discorda na pseudonim (HMAC z solą) i wysyła do backendu tylko pseudonim.
2. **Walidacja i limity** (`limits.py`). Pusty wpis, tekst powyżej 5000 znaków albo zły link dają prośbę o doprecyzowanie bez wywołania modelu. Limit: 5 zapytań na osobę i 30 łącznie na minutę.
3. **Maskowanie danych osobowych** (`pii.py`). PESEL, telefon, e-mail, numery kont, kart i dokumentów zamieniamy na znaczniki (`[PESEL]`), zanim tekst trafi do modelu i do logu.
4. **Agent** (`opencode.py`, `.opencode/`). Backend uruchamia lokalny serwer OpenCode (tylko 127.0.0.1, losowe hasło, odizolowany katalog domowy) i dla każdego pytania tworzy nową sesję bez historii. Agent wykonuje procedurę z `.opencode/agent/prawdowid.md`:
   - Krok 0: walidacja polecenia (odrzuca polecenia spoza zakresu i próby prompt injection),
   - Krok 1: rozbicie na twierdzenia, oddzielenie faktów od opinii,
   - Krok 2: dla każdego twierdzenia wyszukanie dowodów, ocena ich siły i kontekstu, werdykt,
   - Krok 3-4: raport zbiorczy i kontrola, czy odpowiada na pytanie,
   - Krok 5: wynik jako JSON w ustalonym formacie (skill `response-format`).
5. **Kontrola wyniku** (`report.py`). Źródło spoza listy dozwolonych jest usuwane z wyniku. Werdykt „potwierdzone”, „fałszywe” albo „wprowadza w błąd” bez żadnego dozwolonego źródła zamieniamy na „brak wystarczających dowodów”.
6. **Log** (`checklog.py`). Zapisujemy kanał, czas, zamaskowane pytanie, werdykty, źródła, model, czas odpowiedzi, koszt i tokeny, pobrania stron i ich błędy, wstrzymanie się i próby ataku. Strona WWW nie przekazuje żadnego identyfikatora użytkownika. Wpisy starsze niż 7 dni są usuwane automatycznie, a każdy można usunąć od razu.
7. **Wynik.** Strona i bot pokazują pytanie, podsumowanie i dla każdego twierdzenia: werdykt z pewnością, krótką odpowiedź, uzasadnienie, źródła z dosłownym cytatem, uwagi i to, czego nie udało się ustalić. Awaria, limit albo brak klucza są pokazywane jako komunikat, nigdy jako werdykt.

## Bezpieczeństwo agenta

- Uprawnienia w `.opencode/opencode.jsonc`: wszystko zablokowane, dozwolone tylko skille projektu i pobieranie stron z listy stałych hostów (bez `*` w nazwie hosta). Agent nie może uruchamiać poleceń, pisać plików ani pobierać innych adresów.
- Treść pytania i pobranych stron agent traktuje jako dane, nie polecenia. Próby obejścia zasad są odrzucane przez skill walidacji i zapisywane w logu.
- Serwer OpenCode nie widzi zmiennych środowiskowych backendu poza kluczem modelu i nie czyta globalnej konfiguracji komputera.

## Modele i dostawcy

| Dostawca | Przykładowe modele | Uwagi |
|---|---|---|
| Mistral AI (Francja, UE) | `mistral-large-latest`, `mistral-medium-latest` | domyślny w demo i testach |
| Google | `gemini-3.5-flash`, `gemini-3.1-flash-lite` | darmowy plan ma niskie limity (kilka zapytań na minutę) |
| Anthropic, OpenAI | dowolny model obsługiwany przez OpenCode | po ustawieniu `AI_PROVIDER` i `AI_MODEL` |

Dostawcę i model zmienia się w `.env` (`AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`), bez zmian w kodzie. Dane przetwarzane przez dostawcę: zamaskowany tekst pytania i treść pobranych stron publicznych. Koszt i tokeny każdego sprawdzenia są w logu (`GET /api/v1/log`).

## Ograniczenia

- **Tylko zamknięta lista źródeł.** Agent nie pobiera stron spoza listy, także linków podanych przez użytkownika (decyzja bezpieczeństwa, opis w `docs/ZRODLA.md`). Dla artykułu z portalu prosi o wklejenie jego treści.
- **Brak informacji w źródłach to brak werdyktu.** Jeśli oficjalne źródła nie piszą o danej sprawie, wynik to „brak wystarczających dowodów”.
- **Sprzeczne źródła** nie są pokazywane obok siebie. Przy sprzeczności agent wstrzymuje się od werdyktu.
- **Brak daty pobrania źródła** w wyniku (jest data publikacji).
- **Czas odpowiedzi** zależy od modelu i liczby twierdzeń: proste pytania ok. 30 s, a gdy źródła nie mają odpowiedzi, nawet kilka minut (mediana w testach: 56 s). Agent ma na sprawdzenie do 300 s (`AGENT_TIMEOUT`), po tym czasie użytkownik dostaje komunikat, a nie werdykt.
- **Model nie jest deterministyczny.** To samo pytanie może dać inne sformułowanie, a rzadko inny werdykt.
- **Tylko tekst.** Brak analizy obrazów i nagrań.
- **Google Fact Check.** Skill i dostęp do API są dodane, ale w obecnej konfiguracji agent nie ma uprawnienia do tego skilla, a klucz API nie jest przekazywany serwerowi OpenCode. Do czasu poprawki źródłem wtórnym jest PAP.
- **Jedna instancja backendu.** Limity zapytań i log działają w obrębie jednego procesu. Większy ruch wymaga wspólnej bazy i limitera (np. PostgreSQL, Redis).
