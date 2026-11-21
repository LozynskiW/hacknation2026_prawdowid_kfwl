# PRAWDOWID – wymagania funkcjonalne

Źródło: „MSZ – Pełna treść zadania konkursowego” (HackNation 2026). Numery w kolumnie „Źródło” odnoszą się do sekcji tego dokumentu.

**Priorytet:**
- **MUST** – wymaganie podstawowe (MVP). Bez niego projekt nie dostaje punktów za funkcje premiowane.
- **SHOULD** – wymagane w treści zadania, ale nie wymienione wprost w MVP.
- **BONUS** – funkcja premiowana. Oceniana tylko po spełnieniu wszystkich MUST.

---

## 1. Przyjmowanie zgłoszeń

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-01 | System przyjmuje zgłoszenie w postaci tekstu. | Użytkownik wkleja tekst i otrzymuje wynik sprawdzenia. | MUST | §2, §3 |
| FR-02 | System przyjmuje zgłoszenie w postaci adresu URL i odczytuje treść strony. | Podany URL jest pobierany, a twierdzenia wyodrębniane z jego treści. Nieczytelna strona daje komunikat techniczny, nie werdykt. | MUST | §2, §3 |
| FR-03 | System udostępnia responsywny interfejs WWW. | Formularz i wynik działają na telefonie i komputerze. | MUST | §3, §5 |
| FR-04 | System udostępnia co najmniej jeden dodatkowy kanał (SMS, WhatsApp, Messenger, Instagram, Discord lub równoważny) albo adapter demonstracyjny. Wykluczone: platformy niszowe, Telegram, WeChat. | Zgłoszenie wysłane drugim kanałem dostaje odpowiedź w tym kanale. | MUST | §3, §5 |
| FR-05 | Oba kanały korzystają z tej samej logiki weryfikacji. | Dla tego samego zgłoszenia, przy tych samych źródłach, werdykt i dowody są identyczne w obu kanałach (scenariusz G, 100%). | MUST | §5, §6 |
| FR-06 | Obsługa od odebrania wiadomości do wysłania odpowiedzi odbywa się automatycznie. | Brak ręcznych kroków zespołu w całym przebiegu. | MUST | §3, §5 |
| FR-07 | System przyjmuje obraz (zrzut ekranu, zdjęcie) i dźwięk (nagranie). | Patrz FR-60 do FR-64. | BONUS | §1, §3 |

## 2. Analiza zgłoszenia

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-10 | System rozpoznaje jedno lub kilka twierdzeń wymagających sprawdzenia. | Zgłoszenie wielowątkowe jest rozbite na osobne twierdzenia, każde z własnym wynikiem. | MUST | §2, §3 |
| FR-11 | System odróżnia fakty od opinii. | Opinia lub ocena wartościująca dostaje wynik „nie podlega weryfikacji”. | MUST | §1, §2 |
| FR-12 | System rozpoznaje, gdy pytanie wymaga doprecyzowania, i prosi o nie. | Niejasne zgłoszenie daje prośbę o doprecyzowanie, a nie werdykt. | MUST | §2, §5 |
| FR-13 | System rozpoznaje zgłoszenia wykraczające poza zakres usługi. | Takie zgłoszenie dostaje osobny komunikat „poza zakresem”, a nie werdykt. | MUST | §5 |

## 3. Wyszukiwanie i ocena dowodów

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-20 | System wyszukuje informacje w udostępnionym lub jasno opisanym zbiorze źródeł. | Każde użyte źródło znajduje się na liście dostępnej do audytu. | MUST | §2, §3, §5 |
| FR-21 | Zbiór źródeł obejmuje co najmniej dwa typy źródeł, w tym źródła pierwotne lub urzędowe oraz wiarygodne źródła wtórne (chyba że zespół uzasadni inne podejście). | Lista źródeł zawiera typ każdego źródła. | MUST | §3, §5 |
| FR-22 | Korpus demonstracyjny zawiera co najmniej 100 dokumentów lub rekordów z co najmniej 10 domen. | Zliczenie w bazie potwierdza oba progi. | MUST | §5 |
| FR-23 | System ocenia aktualność i znaczenie znalezionych materiałów. | Każdy dowód ma datę publikacji i pobrania. Aktualne materiały są preferowane. | MUST | §2, §5 |
| FR-24 | System ostrzega o materiale archiwalnym. | Dowód starszy niż okno aktualności dla danego typu informacji jest oznaczony w wyniku. | MUST | §5 |
| FR-25 | System wykrywa prawdziwy materiał użyty w złym czasie lub miejscu. | Scenariusz B daje wynik wskazujący brakujący kontekst. | MUST | §1, §6 |
| FR-26 | Przy sprzecznych wiarygodnych źródłach system jawnie pokazuje rozbieżność. | Scenariusz C: obie strony widoczne w wyniku, bez arbitralnej pewności. | MUST | §1, §6 |
| FR-27 | System porównuje źródła i buduje „łańcuch dowodowy” od twierdzenia do materiałów potwierdzających, obalających i uzupełniających kontekst. | Wynik pokazuje dowody pogrupowane według stanowiska. | BONUS | §3 |
| FR-28 | System wyszukuje w źródłach wielojęzycznych i odpowiada po polsku. | Dowód w języku obcym może uzasadniać werdykt, a odpowiedź jest po polsku. | BONUS | §3 |

## 4. Werdykt

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-30 | Dla każdego twierdzenia system przedstawia jeden z wyników: potwierdzone, fałszywe, wprowadzające w błąd, brak wystarczających dowodów, nie podlega weryfikacji. | Każde twierdzenie ma dokładnie jeden z tych wyników albo status z FR-31. | MUST | §2 |
| FR-31 | Awaria techniczna, brak możliwości wykonania sprawdzenia, potrzeba doprecyzowania i wyjście poza zakres nie są werdyktami i są komunikowane oddzielnie. | Statusy te mają inny wygląd i treść niż werdykty i nie zawierają oceny prawdziwości. | MUST | §2, §5 |
| FR-32 | Siła werdyktu wynika z jawnych przesłanek: jakości i aktualności źródeł, zgodności materiału z twierdzeniem oraz liczby niezależnych potwierdzeń. | Wynik pokazuje ocenę siły i przesłanki, z których ona wynika. | MUST | §2, §3 |
| FR-33 | Przy niewystarczających dowodach system wstrzymuje się od rozstrzygnięcia, bez tworzenia pozornej odpowiedzi. | Scenariusz D daje „brak wystarczających dowodów” (miernik ≥ 80%). | MUST | §2, §3, §8 |
| FR-34 | Przy wstrzymaniu się system wyjaśnia, czego nie udało się ustalić. | Wynik zawiera listę braków. | MUST | §2, §5 |
| FR-35 | System nie przesądza o prawdziwości wyłącznie na podstawie domeny, autora, kanału, popularności, liczby udostępnień ani etykiety wygenerowanej przez ten sam model. | Te cechy nie są przesłanką werdyktu. | MUST | §5 |
| FR-36 | Status źródła (np. sankcje UE) nie przesądza o prawdziwości. System może pokazać odrębne, neutralne ostrzeżenie, jeśli informacja jest aktualna, sprawdzalna i istotna. | Ostrzeżenie jest oddzielone od werdyktu i nie zmienia go. | MUST | §5 |

## 5. Prezentacja wyniku

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-40 | System przedstawia zwięzły wynik z krótkim uzasadnieniem. | Każde twierdzenie ma wynik i 1–3 zdania uzasadnienia. | MUST | §2, §3 |
| FR-41 | Odpowiedź jest po polsku, prostym i zrozumiałym językiem. | Brak żargonu technicznego; zrozumiałe dla osoby o niskich kompetencjach cyfrowych. | MUST | §1, §3, §5 |
| FR-42 | System prezentuje materiały wykorzystane do odpowiedzi. | Każdy dowód ma tytuł, wydawcę, datę i link, a w miarę możliwości wykorzystany fragment. | MUST | §2, §3 |
| FR-43 | System oddziela materiały źródłowe od interpretacji modelu. | Cytaty i dane źródłowe są wizualnie odrębne od wyjaśnienia systemu. | MUST | §2 |
| FR-44 | Każda istotna teza faktograficzna przedstawiana jako ustalenie systemu prowadzi do konkretnego źródła. | Pokrycie cytowań ≥ 95%, poprawność cytowań ≥ 85%. | MUST | §1, §5, §6 |
| FR-45 | System zawiera czytelną informację o ograniczeniach odpowiedzi. | Każdy wynik ma sekcję ograniczeń. | MUST | §3 |
| FR-46 | System zachęca użytkownika do samodzielnego zapoznania się z dowodami. | Wynik zawiera odnośniki do źródeł i zachętę do ich sprawdzenia. | SHOULD | §9 |
| FR-47 | Wizualizacja dowodów. | Graficzne przedstawienie łańcucha dowodowego. | BONUS | §8 |

## 6. Bezpieczeństwo usługi

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-50 | Instrukcje znalezione w analizowanych materiałach nie zmieniają zasad działania systemu. | Scenariusz E: instrukcja w źródle jest zignorowana (miernik ≥ 90% odpartych prób). | MUST | §2, §6 |
| FR-51 | System odnotowuje próbę prompt injection. | Zdarzenie jest zapisane w logu. | MUST | §6 |
| FR-52 | System waliduje wejście. | Nieprawidłowe dane wejściowe są odrzucane z komunikatem. | MUST | §5 |
| FR-53 | System limituje liczbę żądań. | Przekroczenie limitu daje komunikat, a nie błąd usługi. | MUST | §5 |
| FR-54 | Brak klucza, limit lub awaria usługi zewnętrznej nie są przedstawiane jako wynik merytoryczny. | Scenariusz J: ujawnienie ograniczenia technicznego bez pozornego wyniku. | MUST | §5, §6 |

## 7. Multimodalność

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-60 | OCR obrazu z tekstem. | Scenariusz F: poprawne odczytanie treści i daty ze zrzutu ekranu oraz ujawnienie ograniczeń analizy. | BONUS | §3, §6 |
| FR-61 | Transkrypcja nagrania. | Twierdzenia są wyodrębniane z transkrypcji. | BONUS | §3 |
| FR-62 | Analiza metadanych obrazu. | Metadane (np. data wykonania) widoczne jako kontekst. | BONUS | §3 |
| FR-63 | Porównywanie obrazów i wyszukiwanie wcześniejszych wystąpień materiału. | Działa tylko przez działające API lub jasno ograniczoną lokalną bazę. Pełnego wyszukiwania odwrotnego nie deklarujemy bez nich. | BONUS | §3, §5 |
| FR-64 | Ujawnienie kosztu, zakresu działania, retencji danych i ograniczeń zewnętrznych API obrazu lub dźwięku. | Opis w dokumentacji. | BONUS (MUST, jeśli użyte) | §5 |

## 8. Zapis przebiegu i obserwowalność

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-70 | System zapisuje przebieg sprawdzenia: pytanie, czas, wykorzystane źródła i wynik. | Każde sprawdzenie ma wpis w logu. | MUST | §3 |
| FR-71 | System rejestruje czas odpowiedzi, wykorzystanie modeli, błędy wyszukiwania, przypadki wstrzymania się i szacunkowy koszt odpowiedzi. | Dane dostępne dla każdego sprawdzenia. | MUST | §5 |
| FR-72 | System przechowuje znacznik czasu publikacji i pobrania każdego materiału. | Pola wypełnione dla wszystkich dokumentów korpusu. | MUST | §5 |

## 9. Prywatność

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-80 | System automatycznie maskuje oczywiste dane osobowe. | PESEL, telefon, e-mail itp. nie trafiają w jawnej postaci do modeli ani logów. | MUST | §5 |
| FR-81 | System stosuje minimalizację danych i określoną retencję. | Dane są usuwane po zdefiniowanym okresie. | MUST | §5 |
| FR-82 | Sesję demonstracyjną można usunąć. | Po usunięciu nie ma śladów sesji w bazie. | MUST | §5 |
| FR-83 | Kontrolowana archiwizacja materiału wskazanego przez użytkownika, zgodna z prawem, warunkami serwisu, retencją i minimalizacją danych. | Archiwizacja ma określoną podstawę prawną, licencję, retencję, kontrolę dostępu i procedurę usunięcia. | BONUS | §3, §5 |

## 10. Pętla informacji (administrator, moderator, analityk)

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-90 | W sprawach wysokiego ryzyka system powiadamia użytkownika wskazanego przez administratora (np. moderatora, analityka). | Powiadomienie trafia do skonfigurowanego odbiorcy. | SHOULD | §2 |
| FR-91 | Dla powtarzających się pytań bez źródeł system powiadamia wskazanego użytkownika. | Alert o powtarzających się podobnych pytaniach bez odpowiedzi. | SHOULD | §2, §3 |
| FR-92 | Nierozstrzygnięte zgłoszenie może utworzyć sprawę moderatora. | Sprawa powstaje automatycznie. | BONUS | §3, §5 |
| FR-93 | System grupuje podobne zgłoszenia. | Scenariusz H: powtórne podobne zgłoszenie tworzy lub aktualizuje **jedną** sprawę (100%). | BONUS | §3, §6 |
| FR-94 | System odróżnia rekomendację przekazania od faktycznego przekazania sprawy. | Brak fałszywego komunikatu o przekazaniu (scenariusz H). | MUST (jeśli FR-92 wdrożone) | §5, §6 |

## 11. Katalog źródeł i integracje

| ID | Wymaganie | Kryterium akceptacji | Priorytet | Źródło |
|---|---|---|---|---|
| FR-100 | Lista źródeł jest dostępna do audytu. | Lista eksportowalna z typem, licencją i datą aktualizacji. | MUST | §5 |
| FR-101 | Otwarty lub wymienny katalog źródeł z zasadami kwalifikowania, aktualizowania i wykluczania. | Źródło można dodać lub wykluczyć konfiguracją, z podanym powodem. | BONUS | §3 |
| FR-102 | Dopasowanie treści, URL lub obrazu do katalogu znanych incydentów albo korpusu zweryfikowanych informacji. | Scenariusz I: dopasowanie pokazane jako kontekst, bez automatycznego werdyktu na podstawie domeny. | BONUS | §3, §6 |
| FR-103 | Sama obecność domeny lub kanału w katalogu incydentów może wyzwalać ostrzeżenie tylko w jawnie określonych przypadkach. | Reguły ostrzeżeń są opisane. | BONUS | §3 |
| FR-104 | Eksport danych do CSV i JSON. | Eksport sprawdzeń i spraw. | BONUS | §3 |
| FR-105 | Integracja z narzędziami analitycznymi (np. OpenCTI, DISARM). | Dane w formacie przyjmowanym przez narzędzie. | BONUS | §3 |

---

## Wymagania niefunkcjonalne (powiązane)

| ID | Wymaganie | Cel | Źródło |
|---|---|---|---|
| NFR-01 | Trafność werdyktu (macro-F1 na obsługiwanych klasach) | ≥ 0,75 | §6 |
| NFR-02 | Mediana czasu od wejścia do odpowiedzi dla tekstu i URL | ≤ 30 s | §6 |
| NFR-03 | Koszt 100 testów (deklarowany i zmierzony) | raportowany, niższy premiowany | §6 |
| NFR-04 | Scenariusze obowiązkowe uruchomione przez jury bez interwencji zespołu | 100% | §6 |
| NFR-05 | Obsługa kanałów oddzielona od logiki weryfikacji; wymiana modelu lub dostawcy bez przebudowy całego systemu | architektura | §5 |
| NFR-06 | Dostępność: responsywny interfejs, czytelny kontrast, język bez wiedzy technicznej | WCAG AA | §5 |
| NFR-07 | Dostęp do demonstracji bezpłatny po stronie usługi; standardowe opłaty operatora (np. SMS) jasno wskazane | – | §2, §5 |
| NFR-08 | Separacja instrukcji systemowych od treści źródeł, ograniczenia narzędzi, ochrona sekretów | – | §5 |
| NFR-09 | Projektowanie z myślą o polskim języku i kontekście instytucjonalnym, z możliwością rozszerzenia na inne języki i obszary | – | §1 |
| NFR-10 | Architektura umożliwiająca podłączanie kolejnych kanałów, modeli i źródeł bez przebudowy | BONUS | §3 |
| NFR-11 | Ograniczenie zależności od dostawców spoza EOG, możliwość audytu lub samodzielnego hostowania, przejrzysta informacja o miejscu przetwarzania danych | BONUS | §3 |
| NFR-12 | Opis wymaganych kluczy, limitów, kosztów, miejsca przetwarzania danych i zachowania podczas awarii | dokumentacja | §5 |
| NFR-13 | Oszacowanie kosztu 1 000 zapytań, kosztu utrzymania kanału i zachowania przy zwiększonym ruchu | dokumentacja | §5 |
| NFR-14 | Uruchomienie przez jury na podstawie instrukcji zespołu (24-godzinne MVP) | – | §5 |

## Ograniczenia i zakazy

1. Nie wolno przedstawiać wyniku modelu językowego jako faktu bez weryfikowalnej podstawy źródłowej.
2. Nie wolno obchodzić zabezpieczeń serwisów i płatnych baz.
3. Nie wolno przesądzać o prawdziwości wyłącznie na podstawie domeny, autora, kanału, popularności, liczby udostępnień ani etykiety wygenerowanej przez ten sam model.
4. Status źródła (w tym sankcje UE) nie może samodzielnie przesądzać o prawdziwości twierdzenia.
5. Nie wolno deklarować pełnego wyszukiwania odwrotnego obrazu bez działającego API lub jasno ograniczonej lokalnej bazy.
6. Nie wolno archiwizować pełnych treści i obrazów bez określenia podstawy prawnej, licencji, retencji, kontroli dostępu i procedury usunięcia.
7. Wynik nie może zależeć od wcześniejszego wpisania odpowiedzi testowej do promptu ani od zakodowania konkretnych przykładów.
8. Klucze API, dane osobowe i sekrety nie mogą znaleźć się w repozytorium ani materiałach demonstracyjnych.
9. Projekt musi respektować prywatność, prawa autorskie, bezpieczeństwo informacji i zasady przejrzystego stosowania SI.

## Warunek brzegowy (§8)

Projekt dostaje punkty za funkcje premiowane tylko wtedy, gdy spełnia wszystkie cztery warunki:
- działa end-to-end bez ręcznej ingerencji twórców (FR-06, NFR-04);
- nie zawiera sfabrykowanych źródeł (FR-20, FR-44);
- poprawnie wstrzymuje się od rozstrzygnięcia przy braku dowodów (FR-33);
- ma dwa działające kanały albo jeden kanał i adapter demonstracyjny (FR-03, FR-04).

## Mapowanie scenariuszy testowych jury (§6) na wymagania

| Scenariusz | Wymagania |
|---|---|
| A. Fakt prosty | FR-30, FR-42, FR-44 |
| B. Kontekst | FR-24, FR-25 |
| C. Sprzeczność | FR-26 |
| D. Brak dowodów | FR-33, FR-34 |
| E. Atak | FR-50, FR-51 |
| F. Multimodalność | FR-60 |
| G. Spójność | FR-05, FR-06, FR-41 |
| H. Pętla informacji | FR-92, FR-93, FR-94 |
| I. URL / incydent | FR-02, FR-35, FR-102 |
| J. Limit API | FR-31, FR-54 |
