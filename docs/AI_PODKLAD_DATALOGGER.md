# MultiChannel datalogger – samostatný podklad pre AI

**Účel:** tento celý súbor vložte alebo priložte do konverzácie s AI pri
plánovaní, obsluhe a vyhodnocovaní dlhodobého merania. Na bežnú konzultáciu
nie je potrebný GitHub ani zdrojový kód. Súbor neobsahuje dáta konkrétneho
experimentu; tie sa doplnia podľa šablóny na konci.

**Stav opisu:** 7. 11. 2026, firmvér **1.0.7-dev**, Raspberry Pi Pico
**RP2040**, overený **MicroPython 1.27.0**. Tento opis nepredpokladá
kompatibilitu s inou doskou alebo verziou. Aktuálny stav skutočného zariadenia
vždy zistite príkazom STATUS; nastavenia uvedené v príkladoch nie sú záväzné.

## 1. Pokyny pre AI, ktorá dostane tento dokument

- Pomáhaj používateľovi po slovensky, vecne a zrozumiteľne. Najprv zisti
  meranú veličinu, jej rozsah, požadovanú časovú odozvu, dĺžku experimentu,
  snímač a dostupné napájanie.
- Rozlišuj existujúcu funkciu, návrh úpravy a funkciu skutočne overenú
  na zariadení. Nevymýšľaj sériové príkazy ani automatické funkcie.
- Nastavenia sa menia **iba fyzickým menu pri zastavenom zázname**.
  Cez serial sú dostupné iba START, STOP, STATUS, HELP a RESET.
- PAUZA/STOP zastavuje **zápis**, nie získavanie a zobrazovanie meraní.
- Nezamieňaj napätie pred deličom, napätie na ADC, RAW kód a fyzikálnu
  veličinu zo snímača. Najprv over jednotky a konfiguráciu.
- Neinterpretuj počet desatinných miest ani 24-bitový kód ako zaručenú
  presnosť. Kompenzácia deliča používa typickú impedanciu ADC, nie kalibráciu.
- Ak chýba údaj, vyžiadaj ho alebo ho výslovne označ ako predpoklad.
  Nepovažuj ticho na seriovej linke za dôkaz STOP.
- Pred prerušením programu cez REPL, resetom, nahrávaním alebo odpojením
  SD musí byť potvrdený STOP/PAUZA. Pred prepisom zálohuj dotknuté súbory
  priamo z dosky. Nevykonávaj reset ako prvý diagnostický krok počas REC.
- Ak používateľ žiada zmenu firmvéru, vyžiadaj príslušné aktuálne súbory
  alebo aktuálny zdrojový balík. Tento text nenahrádza zdrojový kód.

## 2. Čo zariadenie meria

| Funkcia | Dostupnosť a výstup |
| --- | --- |
| Teplota a vlhkosť SHT4x | V oboch vstupných režimoch, °C a % relatívnej vlhkosti |
| Viac teplôt DS18B20 | Spoločná OneWire zbernica; každý senzor má vlastné ROM ID; °C |
| Externý ADS1256 | Osem vstupov AN0–AN7, postupné meranie voči AINCOM |
| Pôvodné analógové vstupy | A1/A2, približne 0–3,3 V, iba pri ADS1256 Off |
| Pôvodné binárne vstupy | B1–B4 s interným pull-up, iba pri ADS1256 Off |
| Batéria | BAT vo voltoch; samostatný vstup, orientačné meranie bez potvrdenej presnosti |
| Záznam | CSV na microSD, nový názov pri každom spustení REC |
| Čas | Externý RTC DS3231; dátum v názve súboru, čas v každom riadku |
| Obsluha | OLED 128 × 64, rotačný enkodér s tlačidlom, USB serial |

**Vstupné režimy sú vzájomne výlučné.** ADS1256 a pôvodné vstupy zdieľajú
GPIO. Softvérová voľba nenahrádza správne prepojenie konektora J3 ani
fyzické odpojenie konfliktujúcich signálov. Zapnutie ADS nevytvorí ďalších
osem vstupov popri A1/A2 a B1–B4.

## 3. Zapojenie a obmedzenia

| Funkcia | GPIO Pico |
| --- | --- |
| I2C0: SHT4x, RTC, OLED | SDA GP8, SCL GP9 |
| SD SPI0 | SCK GP18, MOSI GP19, MISO GP16, CS GP17 |
| OneWire DS18B20 | GP22; existujúci pull-up 4,7 kΩ na 3,3 V |
| Enkodér | CLK GP12, DT GP13, tlačidlo GP15 |
| LED | GP14 |
| Batéria | ADC GP28, ovládanie deliča GP21 |
| Pôvodné A1/A2 | GP26/GP27 |
| Pôvodné B1–B4 | GP2/GP3/GP4/GP5 |

ADS1256 cez J3: SCLK=GP2, DIN=GP3, DOUT=GP4, CS=GP5, DRDY=GP26,
RST=GP27; modul VCC z 5 V, spoločná GND, PDWN na 3,3 V.
GP22 zostáva pre OneWire. Komunikácia ADS je softvérové SPI.
Pre opísané jednopólové meranie je **AINCOM pripojené na GND**.
Napájanie ADS modulu z 5 V neznamená 5 V toleranciu GPIO Pico.

Aktuálna konfigurácia ADS: **PGA=1**, **100 SPS**, referencia v kóde
**VREF=2,503 V** podľa skoršieho merania; nominálne napájanie pre odhad
rozsahu **AVDD=5,0 V**. Referenciu bez nového merania nemeň.

| Voľba v menu | Buffer | Typická efektívna impedancia ADC | Použiteľný rozsah na ANx pri AVDD=5 V, AINCOM=GND |
| --- | --- | --- | --- |
| Imp:Lo(5V) | vypnutý | 150 kΩ | približne 0–5 V |
| Imp:Hi(3V) | zapnutý | 40 MΩ | 0–3 V |

Pri Hi je horná hranica všeobecne **AVDD − 2 V**, nie vždy presne 3 V.
40 MΩ platí pre aktuálnych 100 SPS a nominálne hodiny ADC 7,68 MHz;
80 MΩ by zodpovedalo rýchlosti 50 SPS alebo nižšej. Spomalenie zápisu CSV
alebo zvýšenie priemerovania rýchlosť samotného ADC nemení.
Diferenciálny plný rozsah ±2×VREF/PGA = ±5,006 V neumožňuje priviesť
−5 V na pin ANx pri AINCOM=GND. Vstupné piny musia dodržať svoje hranice.

Lo viac zaťažuje zdroj a potrebuje zdroj s nízkym výstupným odporom.
Hi zdroj zaťažuje menej, ale má menší povolený rozsah. Údaje sú parametre
ADC; nie zmeraná impedancia celého modulu ani záruka presnosti zapojenia.

## 4. Ovládanie na zariadení

### Základné režimy

- **STOP/PAUZA:** meranie a displej pokračujú, na SD sa nezapisuje.
  Otáčanie vyberá položku menu alebo interval.
- **REC:** údaje sa periodicky zapisujú; nastavenia sa nemenia.
  Stlačenie tlačidla ukončí REC do PAUZA.
- **1WIRE:** prehliadanie nájdených DS18B20, teplôt a ROM ID.
  Otáčanie prepína senzor, stlačenie vráti do PAUZA.
- **SyncRTC:** prenesie aktuálny čas interného RTC Pico do externého
  DS3231. Samo nezíska správny čas z PC ani internetu; napriek textu
  konzoly „synchronizovany s PC“ používa existujúci interný čas.
- **Restart:** synchronizuje úložisko a reštartuje Pico; iba zo STOP/PAUZA.

Poradie hlavného menu: **Restart → SyncRTC → ADS1256 → 1WIRE → 5 s →
10 s → … → 300 s**. Číselný interval má krok 5 s. Pri zvolenom číselnom
intervale stlačenie spustí REC. Nie je implementovaný ľubovoľný interval
ani automatické pokračovanie REC po reštarte.

### Podmenu ADS1256

| Položka | Význam |
| --- | --- |
| On | Inicializuje a kalibruje ADS, vyberie AN0–AN7; pri chybe môže On inicializáciu zopakovať |
| Off | Vyberie pôvodné A1/A2 a B1–B4; vyžaduje správne fyzické zapojenie |
| Vzorky | 1, 2, 4, 8, 16 alebo 32 čerstvých vzoriek na kanál |
| RAW: On/Off | Priame ADC kódy alebo napätia |
| Imp:Lo(5V)/Hi(3V) | Vypnutý/zapnutý buffer |
| Del:No / Del:1:K | Bez deliča alebo prevod podľa Rgnd, Rin a impedancie ADC |
| Spat | Návrat do PAUZA |

Zoznam sa na OLED posúva. Šípka označuje výber, `[AKT]` aktívnu voľbu
On/Off. Zmeny sa potvrdzujú stlačením. Pri zmene konfigurácie sa zahodí
rozpracovaná ADS dávka aj staré výsledky, aby nevznikla zmiešaná sada.

## 5. Delič, prepočet a rozsah pred deličom

Jeden spoločný softvérový prevod platí pre všetkých osem AN vstupov.
Na každom použitom kanáli sa predpokladá vlastný fyzický delič s rovnakými
odpormi. Samostatné nastavenie odporov pre každý kanál nie je implementované.

```text
Merané Uin ── Rin ──┬── ANx
                    │
                   Rgnd
                    │
GND ────────────────┴── AINCOM
```

Rgnd je dolný odpor proti GND; Rin horný sériový odpor od zdroja k ANx.
Pre zadávané celé ohmy: **Rgnd=1…99999999 Ω**, **Rin=0…99999999 Ω**.
ADC zaťažuje Rgnd paralelne, preto:

```text
Zadc = 150000 Ω (Lo) alebo 40000000 Ω (Hi)
Rd   = Rgnd || Zadc = 1 / (1/Rgnd + 1/Zadc)
K    = 1 + Rin/Rd = 1 + Rin/Rgnd + Rin/Zadc
Uin  = Uadc × K
```

Menu **Del:1:K** vyjadruje Uadc:Uin. Pri **No** je K=1; zapamätané
odpory sa nepoužívajú. Koeficient sa nepočíta zo zaokrúhleného textu menu.

Horný vypočítaný rozsah Uin je `K × min(Ulimit, 2×VREF)`, kde Ulimit
je AVDD v Lo a AVDD−2 V v Hi. Ide o odhad pri nominálnom napájaní,
nie automatické meranie napájania alebo overenie výkonu a napäťovej
zaťažiteľnosti rezistorov a celého obvodu.

Príklad Rgnd=10000 Ω a Rin=90000 Ω:

| Imp | K | Nominálny rozsah pred deličom |
| --- | --- | --- |
| Lo | 10,6 | približne 0–53 V |
| Hi | 10,00225 | približne 0–30,00675 V |

V **Del** vyberte Rgnd alebo Rin. Otáčanie mení podčiarknutú číslicu,
stlačenie posúva na ďalšiu, po ôsmej číslici sa vrátite do podmenu.
`00010000` znamená 10000 Ω. **Prevod/rozsah** ukazuje navrhovaný K a
rozsah; spodný riadok **Akt:0-…V** je rozsah aktuálne používanej konfigurácie.
Návrh predpokladá zapnutý delič, aj keď je zatiaľ aktívne No.
**Pouzit** zapne a uloží návrh; **No** vypne prepočet a uchová odpory;
**Spat** zahodí rozpracované úpravy. Z náhľadu sa vracia stlačením.

Výpočet nezahŕňa tolerancie rezistorov, výstupný odpor snímača, ďalšie
súčiastky modulu ani dynamické ustálenie po prepnutí kanála. Presnosť
preverujte známymi napätiami v celom plánovanom rozsahu. Výpočet s typickou
Zadc nie je individuálna kalibrácia a fyzicky nechráni vstup pred prepätím.

## 6. RAW, priemerovanie a časovanie

- **RAW Off + Del No:** AN0–AN7 sú napätia na ADC, vo voltoch.
- **RAW Off + zapnutý delič:** AN0–AN7 už sú Uin pred deličom, vo voltoch.
  Pri analýze ich znova nenásob K.
- **RAW On:** AN0_RAW–AN7_RAW sú priame podpísané 24-bitové kódy
  −8388608…8388607. Bez softvérového prepočtu a bez priemerovania.
  Interná kalibrácia ADC zostáva aktívna. RAW nemení napäťové limity.
- Pri RAW On je efektívne N=1; uložené N sa opäť použije po RAW Off.
  Malý záporný kód pri nulovom signále môže byť offset/šum.

Ručný prepočet RAW pri aktuálnom PGA a referencii:

```text
Uadc [V] = RAW × (2 × 2,503 / 8388607)
Uin  [V] = Uadc × K       # iba ak je fyzický delič zapnutý
```

Jeden kód predstavuje približne 0,597 µV na ADC. Nie je to zaručená
presnosť ani využiteľné rozlíšenie celého merania.

Pri RAW Off aplikácia postupne prejde AN0–AN7 N-krát a zverejní všetkých
osem priemerov spolu. V každej iterácii hlavnej slučky získa jeden čerstvý
prevod. Sada potrebuje 8×N iterácií, pri slučke najmenej 50 ms teoreticky
aspoň približne 0,4×N s plus práca periférií; po hotovej sade nasleduje
približne 1 s odstup. Nie je to presne garantovaná obnovovacia frekvencia.
Osem kanálov sa nemeria súčasne a priemery nemajú spoločný okamih vzorkovania.

**100 SPS ADC nie je 100 úplných osemkanálových sád za sekundu.**
CSV ukladá poslednú dokončenú sadu. Pri kratšom intervale zápisu než čase
tvorby sady sa hodnoty v riadkoch môžu opakovať; nepredstieraj viac
nezávislých meraní. Čas CSV je čas zápisu, nie čas každej konverzie.
Vyššie N zlepšuje potlačenie časti náhodného šumu, ale spomaľuje odozvu
a neodstraňuje systematické chyby.

## 7. USB serial – presný zoznam príkazov

Pripojte terminál k aktuálnemu USB portu Pico (na Linuxe typicky
`/dev/ttyACM0`, ale port môže byť iný). Používané nastavenie terminálu
je 115200 baud. Len jedna aplikácia má používať port naraz.
Po reštarte počkajte na pripravenosť USB. Príkazy ukončujte Enter
(LF, CR alebo CRLF), veľkosť písmen nerozhoduje. Limit 32 ASCII znakov.
Prázdny riadok sa ignoruje; po neúplnom prenose odošlite Enter a príkaz
zopakujte. Nie je to Python REPL ani rozhranie na nastavovanie parametrov.

| Príkaz | Podmienky a výsledok |
| --- | --- |
| START | Len z PAUZA so zvoleným číselným intervalom 5–300 s. Spustí REC; prvý zápis až po uplynutí intervalu. |
| STOP | Z REC do PAUZA. Mimo REC iba potvrdí stav, nezatvorí menu ani TEST. |
| STATUS | Číta konfiguráciu a stav z RAM, bez zmeny nastavení a súborov. |
| HELP | Vypíše použitie príkazov. |
| RESET | Len v PAUZA; synchronizuje úložisko a cez machine.reset() reštartuje firmvér. Pri chybe synchronizácie reset odmietne. |

START počas REC nevyrobí druhý záznam ani nezmení časovač. START v menu,
TEST/SYNC alebo pri zvolenej nečíselnej položke hlavného menu sa odmietne.
Príkaz `START 60` nie je podporovaný: interval vyberá človek enkodérom.
STOP mimo REC nezahodí rozpracované nastavenia. Pri REC treba pred RESET
odoslať STOP a počkať na potvrdenie; otvorené menu treba opustiť na doske.

Typické odpovede:

```text
[STATE] mode=PAUZA; serial: START STOP STATUS HELP RESET
[OK] START mode=REC source=SERIAL interval=60s file=/sd/20261107_120000.csv sd=OK
[OK] STOP mode=PAUZA source=SERIAL file=/sd/20261107_120000.csv
[ERR] RESET iba v PAUZA; pouzite STOP a opustite menu
[STATUS] END
```

Zdroj BUTTON znamená fyzické tlačidlo. Počas REC môžu medzi odpoveďami
prichádzať intervalové výpisy hodnôt, úspechu/chyby SD alebo chyby ADC.
V PAUZA nie je periodický heartbeat, ale meranie pokračuje.
STATUS zahŕňa FW/Git/build/dirty, mode, vybraný interval alebo položku,
SD, počet DS, aktuálny/posledný CSV súbor, vstupný režim, RAW, uložené aj
efektívne N, Imp/Zadc, VREF/AVDD, delič/K/rozsah, pripravenosť sady,
chybu ADC a chybu uloženia nastavení. Odpoveď končí `[STATUS] END`.
Pri ADS Off sú vypísané uložené ADS parametre neaktívne; netýkajú sa A1/A2.

**START nie je potvrdenie funkčnej SD ani platného ADC.** Aktuálna logika
umožní REC aj s chýbajúcou SD alebo chybou ADC; STATUS a skutočný záznam
preto treba overiť. STOP sa spracuje medzi iteráciami, nie uprostred
blokujúceho čítania ADC alebo zápisu SD. Presná maximálna odozva nie je
pre celý hardvér zaručená; zahltenie terminálu nie je vhodné.

Ctrl-C preruší celú aplikáciu do REPL. Ctrl-D v REPL vykoná soft reštart.
`mpremote exec` bežiaci program tiež preruší; nepoužívajte ho na odosielanie
aplikačného START/STOP. RESET môže odpojiť USB; po návrate overte STATUS.

## 8. Nastavenia po vypnutí a reštarte

V internej flash sa uchovávajú:

| Súbor | Nastavenie | Bez platného súboru |
| --- | --- | --- |
| input_mode.cfg | ADS On/Off | Off, pôvodné vstupy |
| ads_samples.cfg | Uložené N | 1 |
| ads_raw.cfg | RAW | Off |
| ads_buffer.cfg | Buffer/Imp | Lo |
| ads_divider.cfg | Zapnutie deliča, Rgnd, Rin | No, pripravené odpory 10000/90000 Ω |

Číselný interval ani REC sa trvalo neukladajú. Po štarte je **PAUZA a
interval 60 s**. Automatické pokračovanie po výpadku nie je implementované.
Súbory sa ukladajú cez dočasný súbor a synchronizáciu. Pri chybe je voľba
aktívna v RAM, ale môže sa po reštarte stratiť; menu hlási `Ulozenie CHYBA`.
Pri RAW/Imp opätovné stlačenie hodnotu prepne; pre opakované uloženie
rovnakej hodnoty treba prepnúť tam a späť. Pri deličovi zopakujte Pouzit/No.

## 9. CSV a interpretácia údajov

Oddeľovač je čiarka, desatinná bodka. Na každý REC pripadne nový názov
`YYYYMMDD_HHMMSS.csv`; pri existujúcom názve dostane príponu `_1`, `_2`, …
Súbor fyzicky vznikne až pri prvom zápise. Nie je implementované denné
rozdeľovanie ani automatická rotácia pri veľkosti súboru.

Pevné časti hlavičiek:

```text
# ADS Off
Cas,SHT_T,SHT_H,A1,A2,BAT,BIN,B1,B2,B3,B4
# ADS On, RAW Off
Cas,SHT_T,SHT_H,AN0,AN1,AN2,AN3,AN4,AN5,AN6,AN7,BAT
# ADS On, RAW On
Cas,SHT_T,SHT_H,AN0_RAW,AN1_RAW,AN2_RAW,AN3_RAW,AN4_RAW,AN5_RAW,AN6_RAW,AN7_RAW,BAT
```

Komentáre `# …` vyššie slúžia iba vysvetleniu, v skutočnej CSV hlavičke nie sú.
Za pevnými stĺpcami nasleduje ROM ID každého nájdeného DS18B20 ako názov
jeho samostatného teplotného stĺpca. Počet a identitu senzorov určujte podľa
hlavičky, nie pevnou pozíciou alebo domnienkou o ich fyzickom poradí.

| Stĺpec | Jednotka a význam |
| --- | --- |
| Cas | HH:MM:SS pri zápise; bez dátumu, časového pásma a časovej značky vzorky |
| SHT_T | °C, 2 desatinné miesta |
| SHT_H | % relatívnej vlhkosti, 1 desatinné miesto |
| AN0…AN7 | V, 6 desatinných miest; Uadc alebo už Uin podľa Del |
| AN0_RAW…AN7_RAW | Podpísaný celočíselný kód, nie V |
| A1/A2 | V, 2 desatinné miesta; softvérový delič ADS sa na ne nevzťahuje |
| BAT | V, 2 desatinné miesta; orientačné |
| BIN | Štyri znaky 0/1 v poradí B1–B4 |
| B1…B4 | Jednotlivé stavy vstupov; 0 znamená nízku úroveň, pri kontakte na GND zopnutie |
| ROM ID DS18B20 | Teplota v °C |

CSV neobsahuje verziu firmvéru, Imp, N, Rgnd/Rin, K, kalibráciu, polohu
senzorov ani časové pásmo. Uložte ich ku každému experimentu zvlášť
(napr. text STATUS a vyplnená šablóna nižšie). Z hlavičky ANx samotnej
sa nedá zistiť, či už bol použitý delič. Bez toho neprepočítavajte dáta.

Pre viacdenný súbor zostavte dátum z názvu a prechodov času cez polnoc.
Nevykonávajte jednoduché triedenie len podľa HH:MM:SS. Pri dlhých výpadkoch,
zmene RTC alebo letného času môže byť rekonštrukcia nejednoznačná;
požadujte denník experimentu. Zariadenie nemá automatickú správu časového
pásma; do protokolu zapíšte používanú časovú konvenciu.

## 10. Kvalita údajov a dlhodobá prevádzka

- Pri chybe ADS sa zneplatní celá sada a bunky ANx sú prázdne, nie nuly.
  Pred prvou dokončenou sadou sú tiež prázdne. Ďalšie dávky čítanie opakujú;
  chyba inicializácie môže vyžadovať opätovné potvrdenie On.
- Chyba SHT4x sa v aktuálnom kóde označuje **−99,9** pre T aj H. Tieto
  hodnoty nespracúvajte ako platné meranie prostredia.
- DS18B20 sa priebežne obnovujú približne po 800 ms plus práca slučky.
  Pri výnimke sa môže ponechať staršia hodnota bez osobitného príznaku
  neaktuálnosti. Po inicializácii/reskene sú pripravené nuly do prvého
  úspešného čítania; samotná 0 °C preto nedokazuje ani chybu, ani platnosť.
  Nové senzory sa automaticky stále nevyhľadávajú; sken je pri štarte
  a vybraných úkonoch ovládania vrátane spustenia REC.
- Chyba zápisu SD nastaví nedostupnosť SD; REC môže ďalej bežať bez
  ukladania. Kontrola vloženia/obnovenia SD sa vykonáva v PAUZA približne
  každých 5 s, nie ako automatická oprava počas REC.
- Každý úspešný zápis súbor uzatvorí, flushne a synchronizuje. To nie je
  záruka proti poškodeniu pri každom výpadku napájania alebo chybe karty.
- Nie je implementované vzdialené nastavovanie, NTP, automatický štart
  po výpadku, automatické zálohovanie ani overený alarm plnej SD/batérie.
- Pri dlhom meraní navrhnite stabilné napájanie, dostatok SD, kontrolu
  priebežných záznamov a plán riešenia výpadkov. Výdrž batérie nie je z
  tohto dokumentu známa a BAT nie je záruka zostávajúceho času.

Orientačný počet riadkov za deň je **86400 / interval_s**:

| Interval | Riadkov/deň |
| --- | ---: |
| 5 s | 17280 |
| 60 s | 1440 |
| 300 s | 288 |

Objem odhadujte ako počet riadkov × priemerná dĺžka reálneho riadka
vrátane konca riadka a hlavičky, s rezervou. Počet DS a dĺžka hodnôt
veľkosť menia; kapacitu neurčujte iba z počtu kanálov.

## 11. Možnosti prispôsobenia konkrétnemu meraniu

### Dostupné bez zmeny firmvéru

- Teplota a vlhkosť prostredia; teploty na viacerých miestach cez DS18B20.
  Vyžaduje vhodné umiestnenie a priradenie ROM ID ku konkrétnym bodom.
- Analógové snímače s kompatibilným napäťovým výstupom cez ADS alebo A1/A2.
  AI potrebuje prevodnú charakteristiku snímača a jeho napájanie.
- Vyššie napätie cez overený externý delič pre ADS, s nastavením Rgnd/Rin.
  Rozsah fyzického zapojenia treba overiť samostatne.
- Kontaktné stavy cez B1–B4 pri ADS Off. Ide o stavové vzorkovanie, nie
  počítadlo impulzov; krátke udalosti medzi riadkami sa môžu stratiť.
- Voľba intervalu, N, RAW a Lo/Hi podľa dynamiky a zaťaženia zdroja.

### Vyžaduje hardvér, charakteristiku alebo úpravu firmvéru

- Prevod napätia na tlak, silu, polohu, svetlo či inú veličinu možno robiť
  dodatočne v analýze podľa kalibrácie; firmvér teraz nezapisuje vlastné
  fyzikálne jednotky ani ľubovoľné používateľské prevodné krivky.
- Prúdový výstup potrebuje vhodný a overený merací odpor/prevodník;
  zariadenie nemá konfigurovateľný prúdový vstup iba softvérovou voľbou.
- Termočlánok, RTD alebo odporový snímač sa bez potrebného meracieho
  obvodu a kompenzácií nemení na podporovaný snímač priamym pripojením.
- Samostatné deliace pomery kanálov, offsety, kalibračné krivky, rýchle
  impulzy, simultánne kanály, udalostný záznam, RTC synchronizácia z PC,
  automatické pokračovanie REC, denné súbory a vzdialené nastavenie nie
  sú hotové funkcie; treba ich samostatne navrhnúť a overiť.

Pri návrhu úpravy zachovajte MicroPython, aktuálne GPIO, vzájomnú
výlučnosť vstupov, odozvu obsluhy a nulovú prácu so súbormi v IRQ.
Konfiguráciu meňte iba mimo REC; po zmene nesmie zostať zmiešaná ADS dávka.
Zmenu CSV schémy a fyzikálnych jednotiek treba výslovne zdokumentovať.

## 12. Odporúčaný postup experimentu

1. Definujte veličinu, rozsah, trvanie a najkratšiu zmenu, ktorú treba
   zachytiť. Rozhodnite, či stačí stavové alebo pomalé sekvenčné meranie.
2. Overte skutočné zapojenie, režim ADS, kompatibilitu snímačov, GND,
   napájanie a prípadný delič. Pripojenie odlišného režimu neriešte iba menu.
3. V PAUZA nastavte RAW/Imp/N/Del. Skontrolujte prevod a rozsah známym
   signálom a pri teplotách identitu senzorov. Overte čas RTC a SD.
4. Vyberte číselný interval. Uložte STATUS a doplňte metadáta experimentu.
5. Urobte skúšobný REC aspoň cez viac skutočných zápisových intervalov.
   STOP, skontrolujte existujúci CSV súbor, hlavičku, jednotky, chýbajúce
   bunky a rozumné hodnoty; príkaz START sám nestačí.
6. Spustite finálny REC. Dohodnite si interval kontroly STATUS, rastu
   súboru a napájania. Zabráňte automatickému resetu pri pripojení terminálu.
7. Pred zmenou nastavení, manipuláciou s SD a ukončením použite STOP.
   Zálohujte surové CSV a denník. Zdrojové dáta pri analýze neprepisujte.
8. Pri analýze kontrolujte časové medzery, výpadky, saturáciu, opakované
   sady a chybové hodnoty. Až potom prepočítavajte na fyzikálne jednotky,
   odhadujte trendy alebo vyhodnocujte štatistiku.

## 13. Šablóna, ktorú doplní používateľ pre AI

```text
Cieľ merania a rozhodnutie, ktoré majú dáta podporiť:
Merané veličiny a fyzikálne jednotky:
Očakávané minimum/maximum, najrýchlejšia dôležitá zmena:
Dĺžka merania a požadovaná presnosť:
Snímače, napájanie a prevodná charakteristika/kalibrácia:
Zapojenie, fyzický režim J3, spoločná GND:
Mapa kanál -> miesto/snímač; mapa DS ROM ID -> miesto:
Aktuálny výpis STATUS (vložiť celý až po [STATUS] END):
Číselný interval záznamu:
Rgnd/Rin skutočne osadené na každom kanáli, tolerancie:
Rozdiely od spoločného nastavenia deliča, ak existujú:
Napájanie a záložný zdroj, SD a voľná kapacita:
Časová konvencia, správnosť RTC, dátum a čas štartu:
Overenie známym vstupom a skúšobný CSV:
Názvy priložených CSV a informácia, či ANx už je napätie pred deličom:
Zmeny nastavení, výpadky, manipulácia so snímačmi počas merania:
Požadovaný výstup AI (plán/postup/grafy/štatistika/diagnostika):
```

Od AI žiadajte: navrhnúť nastavenie s odôvodnením, uviesť chýbajúce údaje,
oddeliť overené fakty od predpokladov a pomenovať riziká interpretácie.
Vypočítané rozsahy označovať ako nominálne; odhad neistoty má vychádzať
z merania a kalibrácie, nie z počtu bitov alebo desatinných miest.

## 14. Čo už bolo overené a čo nie

V čase vytvorenia podkladu prešlo **54 testov logiky na PC**. Na Pico s
MicroPythonom 1.27.0 sa pri nasadení 1.0.7-dev overila zhoda aplikačných
súborov, syntax, štart ADC/SD, USB STATUS/HELP, krátky START/STOP,
odmietnutie RESET počas REC a reštart cez RESET v PAUZA. Krátky test
sériového ovládania skončil pred prvým intervalovým zápisom.

To nie je nový dôkaz dlhodobej stability, presnosti ADC, výdrže batérie,
odolnosti voči výpadkom, správnosti každého fyzického deliča ani všetkých
kombinácií senzorov a CSV. Tieto vlastnosti treba overiť pre daný experiment.
Tento dokument opisuje existujúci prístroj; neposkytuje prístup k zariadeniu
ani záruku, že medzitým nebol zmenený firmvér alebo zapojenie.
