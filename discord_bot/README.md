# Bot Discorda PRAWDOWID

Adapter kanału: zbiera zgłoszenie z Discorda, wysyła je do API PRAWDOWID, pokazuje wynik. Nie zawiera logiki weryfikacji – ten sam wynik co w WWW.

## Jak działa
1. Użytkownik: `/sprawdz tresc:… link:…`, wiadomość prywatna do bota albo oznaczenie bota (`@Prawdowid …`).
2. Bot w ≤ 3 s odpowiada „Bot myśli…” (`defer`), żeby Discord nie uznał interakcji za nieudaną.
3. Bot wysyła `POST {PRAWDOWID_API_URL}/api/v1/check` (timeout 60 s). Obsługuje też tryb asynchroniczny: odpowiedź `202 {checkId}` → odpytywanie `GET /api/v1/checks/{checkId}`.
4. Raport zamieniany jest na embedy: podsumowanie + osobny embed dla każdego twierdzenia (werdykt, wyjaśnienie, siła dowodów, maks. 2 źródła, ostrzeżenia, „czego nie ustalono”) + link do pełnego wyniku w WWW.
5. Awaria, timeout, limit, zła odpowiedź API → szary embed „Błąd techniczny – to nie jest wynik sprawdzenia”. Nigdy werdykt.

Kontrakt żądania:
```json
POST /api/v1/check
{ "channel": "DISCORD", "userRef": "<HMAC-SHA256(user_id, BOT_USER_SALT)>",
  "conversationId": "<channel_id>:<interaction_id>", "text": "…", "url": "…|null" }
```
Odpowiedź: `VerificationReport` (`models/report.py`). Bot czyta ją tolerancyjnie (`schemas.py`) – nowe pola po stronie backendu go nie psują.

## Konfiguracja Discorda (jednorazowo)
1. https://discord.com/developers/applications → **New Application** → zakładka **Bot** → **Reset Token** → token do `.env` jako `DISCORD_TOKEN`.
2. **Message Content Intent** – niepotrzebny dla `/sprawdz`, DM i oznaczeń. Włącz tylko, jeśli bot ma czytać zwykłe wiadomości na kanałach (wtedy też `DISCORD_MESSAGE_CONTENT_INTENT=true`).
3. **OAuth2 → URL Generator**: scopes `bot` + `applications.commands`; uprawnienia: *Send Messages*, *Embed Links*, *Read Message History*. Otwórz wygenerowany link i dodaj bota na serwer testowy.
4. ID serwera testowego (tryb deweloperski w Discordzie → PPM na serwer → Kopiuj ID) do `DISCORD_GUILD_ID` – komendy pojawią się od razu.

## Uruchomienie lokalne
```bash
cp .env.example .env           # uzupełnij DISCORD_TOKEN, DISCORD_GUILD_ID, BOT_USER_SALT
uv sync

# terminal 1 – mock API (dopóki backend nie jest gotowy)
uv run uvicorn mock_api.app:app --port 8000

# terminal 2 – bot
uv run python -m discord_bot
```
Przejście na prawdziwy backend: zmień `PRAWDOWID_API_URL` w `.env`.

## Scenariusze mocka (słowo w treści)
| Słowo | Wynik |
|---|---|
| `skażenie` | ❌ Fałszywe + pomiar PAA + rekomendacja przekazania |
| `powódź` | ⚠️ Wprowadza w błąd (materiał archiwalny) |
| `lotnisko` | ✅ Potwierdzone, 2 niezależne źródła |
| `sprzeczne` | ❔ Brak dowodów + rozbieżność źródeł |
| `zignoruj` | ❔ Brak dowodów + odnotowana próba injection |
| `uważam` | 💬 Nie podlega weryfikacji |
| `awaria` | 🛠️ Błąd techniczny (503) |
| `wolno` | tryb asynchroniczny 202 + polling |
| bardzo krótki tekst | ✏️ Prośba o doprecyzowanie |
| inne | ❔ Brak wystarczających dowodów |

Dane mocka są oznaczone „[DANE TESTOWE]” – nie pokazywać ich jako prawdziwych wyników w demo.

## Prywatność i bezpieczeństwo
- Surowe ID Discorda nie opuszcza bota – do API idzie `HMAC-SHA256(id, BOT_USER_SALT)`.
- Bot loguje tylko metadane (ID rozmowy, czas, sukces/porażka), nigdy treść wiadomości.
- Limit: 3 zapytania / 60 s na użytkownika (konfigurowalne); backend ma własny limit.
- Opcja `prywatnie: True` w `/sprawdz` – wynik widzi tylko pytający.
- Token i sól tylko w `.env` (w `.gitignore`).

## Pliki
| Plik | Rola |
|---|---|
| `config.py` | ustawienia z `.env` |
| `api_client.py` | klient API (sync + async/polling, mapowanie błędów na komunikaty techniczne) |
| `schemas.py` | tolerancyjny widok `VerificationReport` |
| `render.py` | raport → embedy (etykiety PL, limity Discorda) |
| `bot.py` | komendy `/sprawdz`, `/pomoc`, DM i oznaczenia, walidacja wejścia, rate limit |
| `__main__.py` | `python -m discord_bot` |
