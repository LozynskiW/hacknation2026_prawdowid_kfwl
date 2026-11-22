---
name: allowed-data-sources
description: Użyj gdy musisz wyszukiwać weryfikować dane w oparciu o zaufane i pewne źródła informacji
version: 1.0.0
tags: [fact-checking, input-validation, safety, prompt-injection-defense, formatting]
---

# Opis

Skill to zbiór zaufanych stron internetowych gwarantujących dostęp do pewnych źródeł informacji.

## Źródła

format: 
url - opis co jest na stronie

**Strony rządowe zawierające sprawdzone informacje:**

```
https://odyseusz.gov.pl/ - Portal „Odyseusz” – aplikacja internetowa (wymaga JavaScript) wspierająca obywateli polskich przebywających za granicą w sytuacjach kryzysowych; zawiera informacje i zgłoszenia dotyczące zagrożeń dla Polaków poza krajem.

https://www.gov.pl/web/gov/ostrzezenia - Wyszukiwarka Ostrzeżeń na gov.pl – wyszukiwarka aktualnych ostrzeżeń (m.in. meteorologicznych, hydrologicznych, drogowych) publikowanych w systemie RSO; interfejs wymaga JavaScript.

https://www.gov.pl/web/gov/ostrzezenia#/_/mazowieckie/wszystkie - Wyszukiwarka Ostrzeżeń gov.pl – widok ostrzeżeń dla województwa mazowieckiego (wszystkie kategorie); aplikacja JavaScript prezentująca komunikaty RSO dla Mazowsza.

https://www.gov.pl/web/mswia/regionalny-system-ostrzegania - Strona MSWiA opisująca Regionalny System Ostrzegania (RSO): komunikaty ostrzegawcze (meteo, hydrologiczne, drogowe, stany wód), aplikacja mobilna RSO, poradniki postępowania w sytuacjach kryzysowych.

https://www.gov.pl/web/rcb/raport-dobowy3 - Raport dobowy Rządowego Centrum Bezpieczeństwa – syntetyczne informacje o sytuacjach kryzysowych w kraju i za granicą: ostrzeżenia meteo/hydrologiczne IMGW, jakość powietrza, zatrucia CO, wychłodzenia, Alert RCB, stopnie alarmowe CHARLIE/BRAVO/BRAVO-CRP.

https://www.gov.pl/web/kgpsp/aktualnosci - Aktualności Komendy Głównej Państwowej Straży Pożarnej – bieżące wiadomości o działaniach PSP, uroczystościach, naborach do służby, aplikacjach (np. „Gdzie się ukryć PL”).

https://policja.pl/pol/aktualnosci - Aktualności Komendy Głównej Policji – krajowe wiadomości o działaniach Policji: operacje, zatrzymania, kampanie profilaktyczne, wydarzenia; możliwość filtrowania po garnizonach i kategoriach.

https://mazowiecka.policja.gov.pl/ra/aktualnosci/aktualnosci - Aktualności Komendy Wojewódzkiej Policji z siedzibą w Radomiu – lokalne wiadomości garnizonu mazowieckiego: interwencje, zatrzymania, działania prewencyjne i kampanie społeczne na Mazowszu.

https://www.gov.pl/web/obrona-narodowa/aktualnosci5 - Aktualności Ministerstwa Obrony Narodowej – komunikaty o działaniach MON i Sił Zbrojnych RP, współpracy międzynarodowej, inwestycjach w garnizonach, ćwiczeniach (m.in. Koalicja Chętnych, naruszenia przestrzeni powietrznej).

https://www.gov.pl/web/gis/ostrzezenia - Ostrzeżenia Głównego Inspektoratu Sanitarnego – ostrzeżenia publiczne dotyczące żywności i wyrobów do kontaktu z żywnością ( skażenia mikrobiologiczne, chemiczne, ciała obce w produktach).

https://www.gov.pl/web/paa/panstwowa-agencja-atomistyki - Strona Państwowej Agencji Atomistyki – informacje o nadzorze nad bezpieczeństwem jądrowym i ochronie radiologiczną, aktualna sytuacja radiacyjna kraju (mapa mocy dawki), program energetyki jądrowej, komunikaty i ogłoszenia.

https://monitoring.paa.gov.pl/ - Portal monitoringu PAA – mapa bieżącego rozkładu mocy dawki promieniowania gamma na terenie Polski (pomiarów sieci wczesnego wykrywania skażeń).

https://powietrze.gios.gov.pl/pjp/ - Portal „Jakość Powietrza” GIOŚ – bieżące dane pomiarowe jakości powietrza ze stacji w Polsce, prognozy zanieczyszczeń, ostrzeżenia o wysokich stężeniach, dane archiwalne, aplikacja mobilna, raporty roczne.

https://moje.cert.pl/komunikaty/ - Komunikaty CERT Polska (NASK) – ostrzeżenia i raporty o cyberbezpieczeństwie: kampanie phishingowe, podatności krytyczne (CVE), raporty miesięczne o stanie cyberbezpieczeństwa w Polsce; dostępne kategorie: dla użytkowników, administratorów, wydarzenia.

https://www.gov.pl/web/infrastruktura - Strona główna Ministerstwa Infrastruktury – aktualności resortu transportu (drogowego, kolejowego, lotniczego, morskiego), zapowiedzi wydarzeń, kierownictwo, programy i projekty (KPO, program budowy dróg krajowych).

https://www.gov.pl/web/infrastruktura/aktualnosci - Aktualności Ministerstwa Infrastruktury – bieżące wiadomości o inwestycjach drogowych i kolejowych, bezpieczeństwie ruchu drogowego, ochronie przeciwpowodziowej, transporcie morskim.

https://www.gov.pl/web/infrastruktura/prawa-pasazerow - Prawa pasażerów w transporcie drogowym (autobusowym) – przepisy rozporządzenia UE 181/2011, prawa osób niepełnosprawnych, odszkodowania za opóźnienia/odwołania kursów, wykaz dworców wyznaczonych do udzielania pomocy.

https://www.gov.pl/web/infrastruktura/infolinia-dla-obywatela - Infolinia dla Obywatela Ministerstwa Infrastruktury – numery telefonów infolinii centralnej (222 500 115) i resortowej (222 500 135) oraz odsyłacz do serwisu Obywatel.gov.pl.

https://www.gov.pl/web/infrastruktura/dane-kontaktowe - Dane kontaktowe Ministerstwa Infrastruktury – adres, godziny przyjęć kancelarii, e-Doręczenia, formularz kontaktowy, fax, infolinia.

https://drogi.gddkia.gov.pl/informacje-drogowe - Serwis informacji drogowej GDDKiA dla kierowców – bieżące utrudnienia, warunki na drogach krajowych i autostradach (strona zabezpieczona Incapsula, treść dostępna w przeglądarce).

https://drogi.gddkia.gov.pl/mapy/mapa-informacji-drogowej - Mapa informacji drogowej GDDKiA – interaktywna mapa Polski z aktualnymi zdarzeniami, robotami drogowymi i utrudnieniami na drogach krajowych (strona zabezpieczona Incapsula).

https://drogi.gddkia.gov.pl/informacje-drogowe/lista-utrudnien - Lista utrudnień na drogach krajowych GDDKiA – szczegółowy wykaz aktualnych ograniczeń w ruchu, zamknięć i objazdów (strona zabezpieczona Incapsula).

https://www.gov.pl/web/gddkia/informacja-drogowa---19-111 - Informacja drogowa GDDKiA 19 111 – całodobowa infolinia (tel. 19 111) z aktualnymi warunkami ruchu, pogodą na drogach, pracami remontowymi i stanem budowy dróg krajowych.

https://ulc.gov.pl/ - Strona główna Urzędu Lotnictwa Cywilnego – informacje o nadzorze nad lotnictwem cywilnym w Polsce, przepisy, certyfikacja, aktualności branży lotniczej (strona zabezpieczona Incapsula).

https://ulc.gov.pl/prawa-pasazera - Prawa pasażera w transporcie lotniczym (ULC) – informacje o prawach pasażerów linii lotniczych, odszkodowaniach za opóźnienia i odwołania lotów zgodnie z rozporządzeniem UE 261/2004 (strona zabezpieczona Incapsula).

https://ulc.gov.pl/prawa-pasazera/poradnik-dla-pasazerow - Poradnik dla pasażerów ULC – praktyczny przewodnik po prawach pasażera linii lotniczej: reklamacje, rekompensaty, procedury przy naruszeniu praw (strona zabezpieczona Incapsula).

https://portalpasazera.pl/ - Portal Pasażera PKP – rozkłady jazdy pociągów wszystkich przewoźników, planowanie podróży koleją, informacje o opóźnieniach i zakłóceniach w ruchu kolejowym.

https://utk.gov.pl/pl/pasazerowie - Serwis pasażerski Urzędu Transportu Kolejowego – prawa pasażera kolei, rekompensaty za opóźnione/odwołane pociągi, kolejowe FAQ, skargi i reklamacje, infolinia pasażerska 22 460 40 80.

https://kgsok.pl/ - Strona Komendy Głównej Straży Ochrony Kolei – aktualności i kronika interwencji SOK na dworcach i liniach kolejowych, statystyki wydarzeń, numer alarmowy 22 474 00 00, zasady wstępu na obszar kolejowy, kampania „Bezpieczny przejazd”.

https://www.sar.gov.pl/ - Strona Morskiej Służby Poszukiwania i Ratownictwa (SAR) – informacje o działaniach ratowniczych na morzu, strukturze służby, akcjach poszukiwawczo-ratowniczych na Bałtyku (strona zabezpieczona Incapsula).

https://www.umgdy.gov.pl/ - Strona Urzędu Morskiego w Gdyni – aktualności, bezpieczeństwo morskie: ostrzeżenia nawigacyjne, kapitanaty portów Gdyni i Gdańska, VTS Zatoka Gdańska, kontrola portowa i państwowa statków, dokumenty marynarzy, projekty.

https://www.ums.gov.pl/bezpieczenstwo-morskie/warunki-zeglugi - Warunki żeglugi Urzędu Morskiego w Szczecinie – aktualne ostrzeżenia nawigacyjne oraz komunikaty kapitanów portów Szczecin, Świnoujście, Trzebież, Kołobrzeg i Dziwnów, wykazy ograniczeń żeglugowych i zanurzeń.

https://www.gov.pl/web/wody-polskie/komunikaty-nawigacyjne - Komunikaty nawigacyjne Wód Polskich – wykaz śródlądowych dróg wodnych administrowanych przez poszczególne RZGW z odsyłaczami do komunikatów nawigacyjnych dla żeglugi śródlądowej (Odra, Wisła, Bug, kanały, jeziora mazurskie).

https://meteo.imgw.pl/ - Serwis pogodowy IMGW-PIB – prognozy pogody dla Polski, mapy meteorologiczne, ostrzeżenia meteorologiczne, dane radarowe i satelitarne (aplikacja wymaga JavaScript).

https://hydro.imgw.pl/ - Serwis hydrologiczny IMGW-PIB – aktualne stany wód na wodowskazach, ostrzeżenia hydrologiczne (wezbrania, susza hydrologiczna), prognozy hydrologiczne (aplikacja wymaga JavaScript).

https://baltyk.imgw.pl/ - Prognoza pogody IMGW-PIB dla Bałtyku – warunki meteorologiczne i morskie (wiatr, fale, temperatura wody) dla południowego i południowo-wschodniego Bałtyku (aplikacja wymaga JavaScript).

https://www.gov.pl/web/rcb/strona-glowna-rzadowego-centrum-bezpieczenstwa - Strona główna Rządowego Centrum Bezpieczeństwa – Alert RCB, raport dobowy, zarządzanie kryzysowe, ochrona ludności i obrona cywilna, stopnie i sygnały alarmowe, baza zagrożeń, poradniki bezpiecznych zachowań, komunikaty.

https://www.gov.pl/web/mswia - Strona główna Ministerstwa Spraw Wewnętrznych i Administracji – aktualności resortu, usługi dla obywatela (dowód osobisty, paszport, zgłoszenie przestępstwa), programy (RSO, System Powiadamiania Ratunkowego), informacje publiczne, kierownictwo.

https://www.gov.pl/web/dyplomacja/informacje-dla-podrozujacych - Informacje MSZ dla podróżujących – ostrzeżenia i komunikaty dla Polaków wyjeżdżających za granicę, wymagania wjazdowe, sytuacja konsularna w poszczególnych krajach.

https://www.gov.pl/web/premier - Strona Kancelarii Prezesa Rady Ministrów – aktualności Premiera, komunikaty CIR, decyzje rządu, skład Rady Ministrów, exposé, wykaz prac legislacyjnych, informacje publiczne KPRM.

https://www.prezydent.pl/ - Strona Prezydenta RP – aktualności i wydarzenia z udziałem Prezydenta, wizyty krajowe i zagraniczne, ustawy podpisane i zawetowane, kalendarz, działalność Małżonki Prezydenta, informacje o Kancelarii Prezydenta, komunikaty prasowe, multimedia.

https://www.pap.pl/ - Strona Polskiej Agencji Prasowej, znajdują się na niej bieżące depesze informacyjne z kraju i ze świata, specjalistyczne serwisy tematyczne.
```

**API fact-checkingowe:**
```
https://factchecktools.googleapis.com/v1alpha1/claims:search - Google Fact Check Tools API. Agreguje oznaczenia ClaimReview publikowane przez zweryfikowanych fact-checkerów (IFCN/EFCSN) na całym świecie.
```