# PRAWDOWID

Weryfikacja informacji na podstawie wiarygodnych źródeł - HackNation 2026, zadanie MSZ.
Użytkownik wpisuje informację albo link, a agent sprawdza twierdzenia w źródłach z listy dozwolonych i zwraca werdykt ze źródłami.

## Układ repozytorium

```
agent/                      definicja agenta weryfikującego
  prawdowid.md              agent: zasady i procedura (kroki 0-5)
  skills/<nazwa>/SKILL.md   skille agenta (walidacja wejścia, twierdzenia, dowody, werdykt, źródła)
  response_format.md        format JSON odpowiedzi, który czyta backend

src/prawdowid/              kod (pakiet Python "prawdowid")
  api/                      backend FastAPI: strona WWW i API dla bota
    app.py                  trasy: /, /wynik, /api/v1/check, /health
    settings.py             ustawienia z .env
    agent.py                prompt systemowy z katalogu agent/
    providers.py            wywołanie dostawcy AI (Gemini, Anthropic, OpenAI)
    report.py               JSON agenta -> raport, filtr listy dozwolonych źródeł
    web_view.py             raport -> widok strony
  web/                      front: szablony Jinja2 (HTMX), CSS, JS (oko)
  discord_bot/              bot Discorda (woła /api/v1/check)

config/                     źródła
  whitelist.txt             adresy dopuszczone jako dowód
  sources.yaml              katalog źródeł z licencjami (audyt)
  govpl_whitelist.json      wszystkie serwisy instytucji na www.gov.pl

scripts/                    budowa korpusu i listy gov.pl
docs/                       opis projektu, wymagania, źródła
data/                       pliki generowane (poza repozytorium)
```

## Uruchomienie

Wymagany Python 3.12 lub nowszy. Z katalogu głównego repozytorium:

```bash
pip install -r requirements.txt
```

To instaluje też pakiet z `src/` w trybie edytowalnym, więc zmiany w kodzie działają bez ponownej instalacji.

W `.env` (nie trafia do repozytorium):

```
AI_PROVIDER=gemini        # gemini | anthropic | openai
AI_API_KEY=...
AI_MODEL=...
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
