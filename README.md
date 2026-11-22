# PRAWDOWID

Weryfikacja informacji na podstawie wiarygodnych źródeł - HackNation 2026, zadanie MSZ.
Użytkownik wpisuje informację albo link, a agent sprawdza twierdzenia w źródłach z listy dozwolonych i zwraca werdykt ze źródłami.

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
    report.py               JSON agenta -> raport, odrzuca źródła spoza listy
    web_view.py             raport -> widok strony
  web/                      front: szablony Jinja2 (HTMX), CSS, JS (oko)
  discord_bot/              bot Discorda (woła /api/v1/check)

config/sources.yaml         katalog źródeł korpusu z licencjami (audyt)
scripts/build_corpus.py     budowa korpusu demonstracyjnego
docs/                       opis projektu, wymagania, źródła
data/                       pliki generowane (poza repozytorium)
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

W `.env` (nie trafia do repozytorium):

```
AI_PROVIDER=gemini        # gemini | anthropic | openai
AI_API_KEY=...            # klucz dostawcy, trafia tylko do serwera OpenCode
AI_MODEL=gemini-3.8-flash
# OPENCODE_BIN=opencode2  # gdy OpenCode jest pod inną ścieżką
# AGENT_TIMEOUT=180       # ile sekund czekamy na agenta
```

Backend i strona WWW (http://localhost:8000/):

```bash
uvicorn prawdowid.api.app:app --port 8000
```

Bot Discorda (opis konfiguracji: [src/prawdowid/discord_bot/README.md](src/prawdowid/discord_bot/README.md)):

```bash
python -m prawdowid.discord_bot
```

## Dokumenty

- [docs/PROJEKT.md](docs/PROJEKT.md) - opis projektu
- [docs/WYMAGANIA.md](docs/WYMAGANIA.md) - wymagania
- [docs/ZRODLA.md](docs/ZRODLA.md) - źródła, licencje i zasady ich kwalifikacji
