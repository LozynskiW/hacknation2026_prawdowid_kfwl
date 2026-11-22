# Źródła Prawdowida

Z jakich źródeł korzysta agent, na jakiej podstawie, jak je dobieramy i aktualizujemy.

## Gdzie jest lista

- **Co agent może pobrać:** reguły `webfetch` w [`.opencode/opencode.jsonc`](../.opencode/opencode.jsonc). OpenCode blokuje agentowi każdy inny adres. Backend (`src/prawdowid/api/sources.py`) tymi samymi regułami sprawdza źródła w wyniku i usuwa źródło spoza listy, zanim użytkownik je zobaczy.
- **Opis stron dla agenta:** skill [`allowed-data-sources`](../.opencode/skills/allowed-data-sources/SKILL.md), czyli 43 strony z opisem, co na nich jest. Agent wybiera z nich stronę pasującą do twierdzenia.
- **Oceny fact-checkerów:** skill [`google-fact-check`](../.opencode/skills/google-fact-check/SKILL.md) (Google Fact Check Tools API).

Agent nie ma wyszukiwarki internetowej i nie przechowuje korpusu. Strony z listy pobiera na żywo w chwili sprawdzania, więc dowód jest aktualny na dzień pytania.

## Źródła aktywne

| Host | Wydawca | Typ | Co tam jest | Podstawa wykorzystania |
|---|---|---|---|---|
| `www.gov.pl` (19 stron) | KPRM, RCB, MSWiA, MSZ, MON, PSP, GIS, Ministerstwo Infrastruktury, Wody Polskie i inne | urzędowe | komunikaty, ostrzeżenia, raporty dobowe, informacje dla podróżnych | treści gov.pl na licencji CC BY-SA 4.0 ([regulamin](https://www.gov.pl/web/gov/regulamin)) |
| `odyseusz.gov.pl` | MSZ | urzędowe | rejestracja podróży, ostrzeżenia dla podróżnych | informacja publiczna |
| `www.prezydent.pl` | Kancelaria Prezydenta RP | urzędowe | aktualności, biografia, komunikaty | informacja publiczna |
| `isap.sejm.gov.pl` | Kancelaria Sejmu | akty prawne | Dziennik Ustaw, Monitor Polski | akty normatywne nie są utworami (art. 4 ustawy o prawie autorskim) |
| `policja.pl`, `mazowiecka.policja.gov.pl` | Komenda Główna Policji, KWP Radom | urzędowe | aktualności, komunikaty | informacja publiczna; cytujemy fragment z linkiem |
| `kgsok.pl` | Komenda Główna Straży Ochrony Kolei | urzędowe | komunikaty i kronika interwencji | informacja publiczna; cytujemy fragment z linkiem |
| `moje.cert.pl` | CERT Polska (NASK) | urzędowe | ostrzeżenia o zagrożeniach w sieci | brak jawnej licencji; cytujemy fragment z linkiem |
| `monitoring.paa.gov.pl` | Państwowa Agencja Atomistyki | pomiary | moc dawki promieniowania | dane publiczne |
| `powietrze.gios.gov.pl` | GIOŚ | pomiary | jakość powietrza | dane publiczne, z podaniem źródła „GIOŚ” |
| `meteo.imgw.pl`, `hydro.imgw.pl`, `baltyk.imgw.pl` | IMGW-PIB | pomiary | pogoda, stany wód, warunki na Bałtyku, ostrzeżenia | dane publiczne, z podaniem źródła „IMGW-PIB” |
| `drogi.gddkia.gov.pl` (3 strony) | GDDKiA | urzędowe | utrudnienia i informacja drogowa | informacja publiczna |
| `ulc.gov.pl` (3 strony), `utk.gov.pl` | Urząd Lotnictwa Cywilnego, Urząd Transportu Kolejowego | urzędowe | prawa pasażerów, komunikaty | informacja publiczna |
| `portalpasazera.pl` | PKP PLK | urzędowe | rozkłady i utrudnienia na kolei | regulamin serwisu; cytujemy fragment z linkiem |
| `www.sar.gov.pl`, `www.umgdy.gov.pl`, `www.ums.gov.pl` | Morska Służba Poszukiwania i Ratownictwa, Urzędy Morskie w Gdyni i Szczecinie | urzędowe | bezpieczeństwo i warunki żeglugi | informacja publiczna |
| `www.pap.pl` | Polska Agencja Prasowa | wiarygodne wtórne | depesze z kraju i ze świata | treści chronione prawem autorskim; tylko krótki cytat z linkiem (prawo cytatu, art. 29) |
| `factchecktools.googleapis.com` | Google (dane ClaimReview od fact-checkerów) | wiarygodne wtórne | oceny twierdzeń przez organizacje fact-checkingowe | [warunki Google APIs](https://developers.google.com/terms); ocenę przypisujemy fact-checkerowi, który ją opublikował |

Razem: 21 hostów, w tym 2 źródła wtórne (PAP i oceny fact-checkerów), a reszta to źródła urzędowe i pomiarowe.

**Przechowywanie.** Nie budujemy kopii treści. W wyniku i w logu sprawdzeń zostaje tylko tytuł, wydawca, data publikacji, link i krótki dosłowny cytat. Log jest usuwany po 7 dniach.

## Zasady kwalifikacji

Źródło trafia na listę, gdy spełnia wszystkie warunki:

1. **Wiarygodny wydawca:**
   - źródła pierwotne: administracja rządowa i jej służby, instytuty pomiarowe, Dziennik Ustaw;
   - źródła wtórne: agencja prasowa o wysokiej reputacji (PAP) albo organizacje fact-checkingowe, których oceny zbiera Google Fact Check (zwykle sygnatariusze IFCN lub EFCSN).
2. **Związek z zadaniem:** bezpieczeństwo, ostrzeżenia, transport, pogoda i środowisko, komunikaty państwa, czyli tematy, w których krąży najwięcej fałszywych alarmów.
3. **Wolno pobierać:** serwis nie blokuje automatów i nie wymaga logowania. Nie obchodzimy zabezpieczeń ani paywalli.
4. **Stały adres hosta:** reguła bez `*` w nazwie hosta. Wzorzec typu `https://*.gov.pl/*` byłby niebezpieczny, bo `*` obejmuje też `/` i pasowałby do `https://obca-strona.com/x.gov.pl/`.

Domena ani status wydawcy nie przesądzają o prawdziwości twierdzenia. Liczą się treść dokumentu, jego data i zgodność z twierdzeniem. Rodzaj źródła wpływa tylko na ocenę siły dowodu.

## Aktualizacja i wykluczanie

- **Aktualność:** strony są pobierane na żywo przy każdym sprawdzeniu, więc nie ma przestarzałej kopii. Agent porównuje datę publikacji z datą pytania i ostrzega o materiale archiwalnym.
- **Dodanie źródła:** po sprawdzeniu punktów 1-4 dopisujemy regułę `webfetch` w `.opencode/opencode.jsonc` i opis strony w skillu `allowed-data-sources`. Backend od razu stosuje tę samą listę.
- **Wykluczenie:** usuwamy regułę i opis, a powód zapisujemy w historii zmian (commit). Źródła wykluczone dotąd: Demagog i AFP Sprawdzam (blokują automaty, HTTP 403), Konkret24 (brak licencji na treść), EUvsDisinfo (robots.txt zabrania pobierania), Rada UE (robots.txt niedostępny).
- **Błędy pobierania:** nieudane lub zablokowane pobranie jest liczone w logu sprawdzeń (`fetch_errors`). Agent obniża wtedy pewność albo wstrzymuje się od werdyktu.

## Linki od użytkownika

Agent pobiera wyłącznie strony z listy dozwolonych, także wtedy, gdy link przysłał użytkownik. To świadoma decyzja ze względów bezpieczeństwa:
- nie pobieramy dowolnych adresów wskazanych z zewnątrz, w tym stron z ukrytymi instrukcjami dla modelu (prompt injection), adresów wewnętrznych i stron, które śledzą odwiedzających;
- system nie łączy się z serwisami, których warunki korzystania nie są sprawdzone.

Gdy link prowadzi poza listę (np. artykuł z portalu informacyjnego), system nie wydaje werdyktu. Zwraca status „Potrzebujemy doprecyzowania” z prośbą o wklejenie treści artykułu albo spornych cytatów. Wklejony tekst jest sprawdzany normalnie: agent wyodrębnia z niego twierdzenia i szuka dowodów w źródłach z listy.

Link do strony z listy (np. komunikat na gov.pl) agent pobiera i sprawdza bezpośrednio.

## Ograniczenia

- **Zakres tematów:** sprawy, o których nie piszą źródła z listy, kończą się „brakiem wystarczających dowodów”.
- **Strony wymagające JavaScript** (np. mapy GDDKiA, wyszukiwarka ostrzeżeń gov.pl) mogą zwrócić niepełną treść.
- **Google Fact Check:** skill i dostęp do API są dodane, ale agent nie ma jeszcze uprawnienia do tego skilla, a klucz API nie jest przekazywany serwerowi OpenCode (szczegóły w `docs/ARCHITEKTURA.md`).
