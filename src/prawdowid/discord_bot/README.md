# Bot Discorda PRAWDOWID

Adapter kanału: zbiera zgłoszenie z Discorda, wysyła je do API PRAWDOWID, pokazuje wynik. Nie zawiera logiki weryfikacji – ten sam wynik co w WWW.

## Jak działa
1. Użytkownik: `/sprawdz tresc:…` (link można wkleić w treści), wiadomość prywatna do bota albo oznaczenie bota (`@Prawdowid …`).
2. Bot w ≤ 3 s odpowiada „Bot myśli…” (`defer`), żeby Discord nie uznał interakcji za nieudaną.
3. Bot wysyła `POST {PRAWDOWID_API_URL}/api/v1/check` (timeout 240 s, `PRAWDOWID_API_TIMEOUT`; dłużej niż backend czeka na agenta). Obsługuje też tryb asynchroniczny: odpowiedź `202 {checkId}` → odpytywanie `GET /api/v1/checks/{checkId}`.
4. Raport zamieniany jest na embedy jak wynik na stronie WWW: pytanie użytkownika, podsumowanie i zliczenie werdyktów (kolor jak oko na stronie), potem osobny embed dla każdego twierdzenia (werdykt z pewnością, krótka odpowiedź, uzasadnienie, maks. 3 źródła z cytatem, siła dowodów, uwagi, „czego nie ustalono”).
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
`.env` w katalogu głównym repozytorium uzupełniony o `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `BOT_USER_SALT`. Bot czyta ten plik niezależnie od katalogu, z którego go uruchomisz:
```bash
# terminal 1 - backend
uvicorn prawdowid.api.app:app --port 8000

# terminal 2 - bot
python -m prawdowid.discord_bot
```
Adres backendu: `PRAWDOWID_API_URL` w `.env`.

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
| `__main__.py` | `python -m prawdowid.discord_bot` |
