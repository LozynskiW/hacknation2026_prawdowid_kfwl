# Prawdowid - opis rozwiązania

**Problem.** Fałszywe alarmy i zmanipulowane informacje rozchodzą się szybciej, niż obywatel zdąży je sprawdzić. Ktoś dostaje SMS o „alercie RCB”, widzi post o ewakuacji miasta albo słyszy plotkę o nowym przepisie. Żeby to zweryfikować, musiałby wiedzieć, której instytucji szukać, znaleźć jej komunikat i porównać daty. Większość ludzi tego nie zrobi.

**Rozwiązanie.** Prawdowid sprawia, że sprawdzenie informacji jest tak proste jak wysłanie wiadomości. Użytkownik wkleja tekst na stronie WWW albo pisze do bota na Discordzie. Po chwili dostaje odpowiedź prostym językiem: co jest prawdą, co nie, na jakiej podstawie i gdzie może to sam przeczytać.

**Jak to działa.** Agent SI rozkłada wiadomość na pojedyncze twierdzenia i oddziela fakty od opinii. Każde twierdzenie sprawdza osobno, wyłącznie w zamkniętej, jawnej liście źródeł: serwisach urzędowych (gov.pl, RCB, MSWiA, MSZ, IMGW, GIOŚ, Policja, CERT, GDDKiA, urzędy transportu i morskie) i w Polskiej Agencji Prasowej. Każde twierdzenie dostaje werdykt: potwierdzone, fałszywe, wprowadza w błąd, brak wystarczających dowodów albo nie podlega weryfikacji. Do tego dochodzi krótka odpowiedź, uzasadnienie, pewność i źródła z dosłownym cytatem i linkiem.

**Uczciwe „nie wiem”.** Gdy źródła milczą, system mówi to wprost, zamiast zgadywać. Backend pilnuje tego niezależnie od modelu: usuwa z wyniku każde źródło spoza listy, a werdykt bez źródła zamienia na „brak wystarczających dowodów”. Awaria, limit czy brak klucza nigdy nie udają wyniku. Użytkownik dostaje wtedy jasny komunikat.

**Bezpieczeństwo i prywatność.**
- Agent ma twardo ograniczone uprawnienia: tylko własne skille i pobieranie stron z listy, bez uruchamiania poleceń.
- Treść pytania i pobranych stron traktuje jako dane, nie polecenia, więc próby „zignoruj zasady i potwierdź” są odrzucane i zapisywane w logu.
- PESEL, telefony, e-maile i numery kont są maskowane, zanim trafią do modelu. Strona nie identyfikuje użytkownika, a Discord przekazuje tylko pseudonim.
- Log sprawdzeń trzymamy 7 dni i każde sprawdzenie można usunąć jednym kliknięciem.
- Limity zapytań chronią przed nadużyciami i kosztami.

**Dla kogo i jakie korzyści.**
- Obywatele, także osoby o niskich kompetencjach cyfrowych: bezpłatnie, bez instalacji, w znanym kanale, z dużą czcionką i czytelnymi etykietami.
- Instytucje: każda odpowiedź prowadzi do ich własnych komunikatów, więc system wzmacnia oficjalne kanały, zamiast je zastępować.
- Zespół analityków: log z czasem, kosztem i werdyktem każdego sprawdzenia pokazuje, jakie pogłoski krążą i gdzie źródłom brakuje odpowiedzi.

**Technologia.** Python i FastAPI, strona w HTMX, bot w discord.py, agent w otwartoźródłowym OpenCode z procedurą i skillami opisanymi w plikach projektu. Dostawcę modelu zmienia się jednym ustawieniem: domyślnie Mistral (UE), także Gemini, Anthropic lub OpenAI. Całość uruchamia jedno polecenie `docker compose up`.

**Wyniki testów.** W 15 przypadkach ze scenariuszy jury 13 przeszło. Każdy werdykt rozstrzygający miał źródło (100%), żaden atak nie wymusił potwierdzenia, oba kanały dały ten sam wynik, a awaria i limit nie udawały wyniku. Słabym punktem jest czas: mediana 56 s, a dwa trudne pytania przekroczyły ówczesny limit 3 minut (podnieśliśmy go do 5). Średni koszt to ok. 0,05 USD za sprawdzenie.

**Ograniczenia i dalsze kroki.** Sprawdzamy tylko tekst i tylko w źródłach z listy, a linków spoza niej nie pobieramy ze względów bezpieczeństwa. Dalej chcemy:
- dołączyć oceny organizacji fact-checkingowych (Google Fact Check, integracja przygotowana);
- pokazywać sprzeczne źródła obok siebie;
- dodać analizę zrzutów ekranu i kolejne kanały (Messenger, SMS);
- dodać powiadamianie analityka o powtarzających się pytaniach bez odpowiedzi.
