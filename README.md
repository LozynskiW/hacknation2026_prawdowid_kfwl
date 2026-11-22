# PRAWDOWID

Weryfikacja informacji na podstawie wiarygodnych źródeł - HackNation 2026, zadanie MSZ.
Użytkownik wpisuje informację albo link, a agent sprawdza twierdzenia w źródłach z listy dozwolonych i zwraca werdykt ze źródłami.

## Dla jury: szybki start

Potrzebny jest Docker z Compose (np. Docker Desktop) i własny klucz do modelu językowego, np. Mistral (https://console.mistral.ai) albo Gemini (https://aistudio.google.com/apikey). Naszych kluczy nie ma w repozytorium.

1. Skopiuj wzór ustawień i wpisz w nim swój klucz (`AI_API_KEY`), a dla bota także `DISCORD_TOKEN` i `BOT_USER_SALT`:

   ```bash
   cp .env.example .env
   ```

2. Uruchom stronę i API (bez bota wystarczy sam klucz modelu):

   ```bash
   docker compose up --build app
   ```

   albo stronę, API i bota Discorda:

   ```bash
   docker compose up --build
   ```

3. Otwórz http://localhost:8000 i wpisz informację do sprawdzenia, np. „Czy prezydentem Polski jest Karol Nawrocki?”.

Specyfikacja API: http://localhost:8000/docs (również [docs/openapi.json](docs/openapi.json)).

| Dokument | Zawartość |
|---|---|
| [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) | architektura, przepływ danych, modele i dostawcy, ograniczenia |
| [docs/ZRODLA.md](docs/ZRODLA.md) | źródła, licencje, zasady kwalifikacji i aktualizacji |
| [docs/TESTY.md](docs/TESTY.md) | wyniki testów (scenariusze A-J) i jak je odtworzyć |
| [docs/RYZYKA.md](docs/RYZYKA.md) | najważniejsze ryzyka i sposoby ich ograniczania |
| [docs/OPIS.md](docs/OPIS.md) | opis rozwiązania |

## Układ repozytorium

```
.opencode/                  agent weryfikujący w OpenCode V2 (konfiguracja projektu)
  opencode.jsonc            uprawnienia agenta: tylko skille i pobieranie stron z listy
  agent/prawdowid.md        agent: zasady i procedura (kroki 0-5)
  skills/<nazwa>/SKILL.md   skille agenta (walidacja wejścia, twierdzenia, dowody, werdykt,
                            źródła, format odpowiedzi)

src/prawdowid/              kod (pakiet Python "prawdowid")
  api/                      backend FastAPI: strona WWW i API dla bota
    app.py                  trasy: /, /wynik, /api/v1/check, /health
    settings.py             ustawienia z .env
    opencode.py             uruchamia serwer OpenCode i wysyła mu pytania
    sources.py              lista dozwolonych źródeł (z .opencode/opencode.jsonc)
    pii.py                  maskowanie danych osobowych przed modelem i logiem
    checklog.py             log sprawdzeń (SQLite) z retencją i usuwaniem
    limits.py               walidacja wejścia i limit zapytań
    report.py               JSON agenta -> raport, odrzuca źródła spoza listy
    web_view.py             raport -> widok strony
  web/                      front: szablony Jinja2 (HTMX), CSS, JS (oko)
  discord_bot/              bot Discorda (woła /api/v1/check)

tests/scenarios/            pytania testowe (scenariusze A-J) i skrypt, który je uruchamia
docs/                       opis, architektura, źródła, testy, ryzyka, OpenAPI
Dockerfile, docker-compose.yml   obraz i uruchomienie jednym poleceniem
.env.example                wzór ustawień (bez kluczy)
data/                       pliki generowane: log sprawdzeń, stan OpenCode (poza repozytorium)
```

## Uruchomienie

Wymagany Python 3.12 lub nowszy oraz OpenCode V2 (pakiet npm `@opencode/cli`, polecenie `opencode2`). Z katalogu głównego repozytorium:

```bash
pip install -r requirements.txt
```

To instaluje też pakiet z `src/` w trybie edytowalnym, więc zmiany w kodzie działają bez ponownej instalacji.

```bash
npm install -g @opencode/cli
```

W `.env` (nie trafia do repozytorium; wzór z opisami: [.env.example](.env.example)):

```
AI_PROVIDER=gemini        # gemini | mistral | anthropic | openai
AI_API_KEY=...            # klucz dostawcy, trafia tylko do serwera OpenCode
AI_MODEL=gemini-3.8-flash
# OPENCODE_BIN=opencode2  # gdy OpenCode jest pod inną ścieżką
# AGENT_TIMEOUT=300       # ile sekund czekamy na agenta
# LOG_RETENTION_DAYS=7    # po ilu dniach wpisy logu sprawdzeń są usuwane
# ADMIN_TOKEN=...         # dostęp do /api/v1/log spoza tego komputera
# MAX_TEXT_CHARS=5000     # maks. długość sprawdzanego tekstu
# RATE_LIMIT_PER_MINUTE=5 # zapytania na osobę na minutę (IP strony / pseudonim z Discorda)
# RATE_LIMIT_GLOBAL_PER_MINUTE=30  # zapytania łącznie na minutę
```

Mistral zamiast Gemini:

```
AI_PROVIDER=mistral
AI_API_KEY=...            # klucz z console.mistral.ai
AI_MODEL=mistral-medium-latest
```

Backend i strona WWW (http://localhost:8000/):

```bash
uvicorn prawdowid.api.app:app --port 8000
```

Bot Discorda (opis konfiguracji: [src/prawdowid/discord_bot/README.md](src/prawdowid/discord_bot/README.md)):

```bash
python -m prawdowid.discord_bot
```

## Docker (jedno polecenie)

Wymagany Docker z Compose (np. Docker Desktop) i uzupełniony plik `.env` w katalogu głównym, taki sam jak wyżej. Do `.env` dla bota dopisz `DISCORD_TOKEN` i `BOT_USER_SALT`. Python ani OpenCode nie są potrzebne na komputerze, bo są w obrazie.

```bash
docker compose up --build
```

Uruchamia dwa kontenery:
- `app`: strona WWW i API pod http://localhost:8000 oraz agent OpenCode;
- `bot`: bot Discorda, który łączy się z `app` w sieci Dockera i startuje, gdy `app` jest gotowy.

Przydatne warianty:

| Co | Polecenie |
|---|---|
| Tylko strona i API, bez bota | `docker compose up --build app` |
| Inny port strony | `PRAWDOWID_PORT=8080 docker compose up --build` |
| Praca w tle i logi | `docker compose up -d --build`, potem `docker compose logs -f` |
| Zatrzymanie | `docker compose down` (log sprawdzeń zostaje w wolumenie `prawdowid-data`) |
| Zatrzymanie i usunięcie danych | `docker compose down -v` |

Gdy budowa kończy się błędem `open ~/.docker/buildx/current: permission denied`, ten plik należy do `root` (zwykle po wcześniejszym `sudo docker ...`). Oddaj go swojemu użytkownikowi:

```bash
sudo chown "$(whoami)" ~/.docker/buildx/current
```

Podgląd logu sprawdzeń (`/api/v1/log`) z przeglądarki wymaga `ADMIN_TOKEN` w `.env`, bo dla backendu w kontenerze przeglądarka nie jest „tym samym komputerem”. Bez tokenu można go odczytać z wnętrza kontenera:

```bash
docker compose exec app python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/log').read().decode())"
```

## Log sprawdzeń i prywatność

Każde sprawdzenie (strona i Discord) trafia do `data/prawdowid.db` (SQLite, poza repozytorium). Zapisujemy:
- kanał, czas i pytanie po zamaskowaniu danych osobowych (PESEL, telefon, e-mail, numery kont, kart i dokumentów);
- wynik, werdykty i źródła;
- model, czas odpowiedzi, koszt i tokeny z OpenCode;
- pobrania stron i ich błędy, wstrzymanie się oraz próby prompt injection.

Strona WWW nie identyfikuje użytkownika. Discord przekazuje tylko pseudonim (HMAC z solą).

Dane osobowe maskujemy, zanim tekst trafi do modelu. Wpisy starsze niż `LOG_RETENTION_DAYS` (domyślnie 7 dni) usuwamy automatycznie.

| Co | Jak |
|---|---|
| Podgląd logu i podsumowania (mediana czasu, koszt, wstrzymania, ataki) | `GET /api/v1/log` - z tego komputera albo z `Authorization: Bearer <ADMIN_TOKEN>` |
| Jeden wpis | `GET /api/v1/log/{checkId}` |
| Usunięcie sprawdzenia | przycisk „Usuń teraz” pod wynikiem, `/usun <checkId>` w bocie albo `DELETE /api/v1/checks/{checkId}` |

Konsola backendu pokazuje jedną linię na każde sprawdzenie, bez treści pytania.

## Dokumenty

- [docs/OPIS.md](docs/OPIS.md) - opis rozwiązania
- [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) - architektura, przepływ danych, modele, dostawcy, ograniczenia
- [docs/ZRODLA.md](docs/ZRODLA.md) - źródła, licencje i zasady ich kwalifikacji
- [docs/TESTY.md](docs/TESTY.md) - wyniki testów i jak je odtworzyć
- [docs/RYZYKA.md](docs/RYZYKA.md) - ryzyka i sposoby ich ograniczania
- [docs/PROJEKT.md](docs/PROJEKT.md) - założenia projektu
- [docs/WYMAGANIA.md](docs/WYMAGANIA.md) - wymagania z treści zadania
- [docs/openapi.json](docs/openapi.json) - specyfikacja API (OpenAPI)
