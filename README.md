# Multi-Channel DataLogger (RPi Pico)

Tento projekt predstavuje robustný amatérsky datalogger postavený na mikrokontroléri Raspberry Pi Pico. Zariadenie monitoruje teplotu, vlhkosť, analógové napätia, binárne vstupy a stav batérie.

## 📷 Prvá verzia zariadenia

Prvá fyzická verzia dataloggera v kryte s OLED displejom a rotačným
ovládačom. Fotografie ukazujú hotovú zostavu, vnútorné zapojenie a
pripojenie externého modulu ADS1256.

![Prvá verzia dataloggera s príslušenstvom](docs/photos/v1/zariadenie.jpg)

| Vnútorné zapojenie | OLED displej |
|---|---|
| ![Vnútorné usporiadanie prototypu a batéria](docs/photos/v1/vnutorne-zapojenie.jpg) | ![Zobrazenie údajov na OLED displeji](docs/photos/v1/displej.jpg) |

[Kompletná galéria prvej verzie zariadenia](docs/photos/v1/README.md)
obsahuje aj ďalšie pohľady a externý modul ADS1256. Fotografie dokumentujú
prototyp; aktuálne zapojenie je uvedené v hardvérovej dokumentácii.

## 🚀 Kľúčové vlastnosti

- **Meranie prostredia:** SHT4x pre teplotu a relatívnu vlhkosť.
- **Viacbodové meranie teploty:** viacero senzorov DS18B20 na zbernici OneWire.
- **Analógové vstupy:** dva ADC vstupy 0–3,3 V.
- **Monitorovanie batérie:** meranie napätia batérie cez samostatný ADC vstup; táto časť hardvéru a firmware je stále vo vývoji.
- **Binárne vstupy:** štyri digitálne vstupy pre sledovanie logických stavov.
- **Záznam dát:** ukladanie meraní vo formáte CSV na microSD kartu.
- **Používateľské rozhranie:** SSD1306 OLED displej a rotačný enkodér s tlačidlom.
- **Presný čas:** externý RTC DS3231 synchronizovaný s interným RTC Raspberry Pi Pico.

## 🛠 Hardvérová konfigurácia
| Komponent            | Pin (GP)            | Funkcia                             |
|----------------------|---------------------|-------------------------------------|
| I2C0 (SDA/SCL)       | 8 / 9               | OLED, RTC DS3231, SHT4x             |
| SPI0 (SCK/MOSI/MISO) | 18/19/16            | SD Karta                            |
| SD Card CS           | 17                  | Chip Select pre SD                  |
| OneWire (DS18B20)    | 22                  | Teplotné senzory                    |
| Rotačný enkodér      | 12 (CLK), 13 (DT)   | Ovládanie menu (IRQ)                |
| Tlačidlo enkodéra    | 15                  | Prepínanie režimov (Pauza/REC/Test) |
| Binárne vstupy       | 2, 3, 4, 5          | Digitálne vstupy (Pull-up)          |
| ADC Vstupy           | 26, 27              | Analógové meranie                   |
| Battery Monitor      | 28 (ADC), 21 (CTRL) | Meranie batérie cez tranzistory     |
| Stavová LED          | 14                  | Signalizácia zápisu a chýb          |

## 📁 Štruktúra projektu

- `firmware/` — MicroPython firmware pre Raspberry Pi Pico
- `hardware/schematic/` — KiCad projekt, schéma, PCB a lokálne knižnice
- `hardware/enclosure/` — podklady pre mechanickú konštrukciu
- `docs/data/` — ukážkové namerané dáta
- `docs/datasheet/` — technická dokumentácia použitých komponentov

Podrobnosti o firmware sú v [`firmware/README.md`](firmware/README.md).

Dokumentácia hardvéru a KiCad projektu je v
[`hardware/schematic/README.md`](hardware/schematic/README.md).

## ⚙️ Prevádzkové režimy

- **PAUZA** — zariadenie vykonáva merania a zobrazuje aktuálne hodnoty, ale nezapisuje ich na SD kartu. Enkodérom je možné zvoliť režim alebo interval záznamu.
- **REC** — namerané údaje sa ukladajú na SD kartu v nastavenom intervale. Pre každý záznam sa vytvorí nový CSV súbor s názvom `YYYYMMDD_HHMMSS.csv`.
- **1WIRE** — umožňuje prechádzať pripojené DS18B20 senzory a zobrazovať ich ROM ID a aktuálnu teplotu. Otočením enkodéra sa vyberá senzor, stlačením sa vrátite do PAUZA. Ak sa žiadny senzor nenájde, displej zobrazí `Ziadne senzory!`.
- **Restart** — v PAUZA vyberte túto položku a stlačte enkodér. Zariadenie synchronizuje súborový systém a reštartuje Pico, čím znovu spustí aplikáciu. Počas REC nie je táto voľba dostupná.
- **SyncRTC** — synchronizuje externý RTC DS3231 s aktuálnym časom interného RTC Raspberry Pi Pico.

V PAUZA sa otočením enkodéra vyberá **Restart → SyncRTC → ADS1256 →
1WIRE → 5 až 300 s**. Stlačením sa otvorí zvolená položka alebo spustí
záznam s vybraným intervalom. Interval sa nastavuje v krokoch po 5 sekundách.
Počas REC sa stlačením enkodéra záznam zastaví a zariadenie sa vráti do PAUZA.

Podrobný popis ovládania a režimov je v
[`firmware/README.md`](firmware/README.md).

### ADS1256 – výber vstupov a priemerovanie

Pri vypnutom logovaní (**PAUZA**) vyberte **ADS1256** a stlačte enkodér.
Otočením vyberte **On** alebo **Off** a stlačením potvrďte:

- **On** — zapne ADS1256 a meranie ôsmich vstupov AN0–AN7.
- **Off** — obnoví pôvodné dva analógové vstupy A1/A2 a štyri digitálne vstupy B1–B4.

Otočenie iba posúva výber; zmena sa vykoná až potvrdením a platí ihneď
bez reštartu. Značka `>` označuje výber, `[AKT]` aktuálny vstupný režim.
Oba režimy zdieľajú GPIO a vyžadujú zodpovedajúce zapojenie J3. Pred
pripojením pôvodných vstupných signálov odpojte modul ADS1256.

V **ADS1256 → Vzorky** možno zvoliť **1, 2, 4, 8, 16 alebo 32 vzoriek
na kanál**. Stlačením sa počet potvrdí a zobrazí sa podmenu ADS1256;
položkou **Spat** sa vrátite do PAUZA. Displej aj CSV používajú aritmetický
priemer čerstvých meraní; vyšší počet predlžuje čas aktualizácie.
Počas REC sa vstupný režim ani počet vzoriek nedajú meniť.

Voľba On/Off a počet vzoriek sa ukladajú samostatne do internej pamäte
Pico a obnovia sa aj po odpojení napájania. Bez platného nastavenia sa
použije **Off** a **1 vzorka**. Pri chybe uloženia sa zobrazí
`Ulozenie CHYBA`; voľba platí v pamäti RAM, ale uloženie treba zopakovať.

Podrobné ovládanie, aktualizácia firmvéru a oba CSV formáty sú vo
[`firmware/README.md`](firmware/README.md). Tabuľka GPIO vyššie a CSV
hlavička nižšie opisujú pôvodné vstupy, teda **ADS1256 Off**.

## 💾 Formát dát (CSV)

Pri spustení režimu **REC** sa vytvorí nový CSV súbor s názvom odvodeným
od aktuálneho dátumu a času. Do rovnakého súboru sa zapisuje až do
ukončenia režimu REC.

Pevná časť CSV hlavičky je:

```text
Cas,SHT_T,SHT_H,A1,A2,BAT,BIN,B1,B2,B3,B4
```
Za ňou firmware pridá ROM ID jednotlivých detegovaných DS18B20 senzorov
ako ďalšie stĺpce.
Príklad nameraných dát je v adresári [`docs/data/`](docs/data/).

## 🛡 Stabilita záznamu

- **Obsluha enkodéra cez IRQ:** enkodér je spracovávaný pomocou prerušenia.
- **Zápis na SD kartu:** po zápise dát firmware používa `flush()` a `uos.sync()` na prenesenie dát do súborového systému.
- **Správa pamäte:** firmware pravidelne používa garbage collection (`gc.collect()`).

## 🔌 Zapojenie

Detailné elektrické zapojenie je dostupné v KiCad projekte v
[`hardware/schematic/`](hardware/schematic/).

### 1. I2C zbernica (GP8, GP9)

Na spoločnej I2C zbernici sú pripojené:

- OLED displej SSD1306
- RTC DS3231
- senzor teploty a vlhkosti SHT4x

SDA a SCL vyžadujú pull-up rezistory. Pri použití hotových modulov je
potrebné overiť, či ich už moduly obsahujú.

### 2. microSD karta (SPI0)

microSD karta komunikuje s Raspberry Pi Pico cez SPI0:

| Signál | GPIO |
|---|---:|
| SCK | GP18 |
| MOSI | GP19 |
| MISO | GP16 |
| CS | GP17 |

Komunikačné signály microSD karty pracujú s logickými úrovňami 3,3 V.

### 3. OneWire (GP22)

DS18B20: Všetky senzory paralelne (Data na GP22, VCC na 3.3V, GND).
Pull-up: Medzi GP22 a 3.3V musí byť odpor 4.7kΩ.

### 4. Monitorovanie batérie

Napätie batérie sa meria pomocou ADC na GP28, pričom GP21 slúži na
ovládanie meracieho obvodu.

Hardvérové zapojenie a spôsob merania batérie sú stále vo vývoji a môžu
sa zmeniť. Aktuálne zapojenie je zdokumentované v KiCad schéme.

### 5. Ovládacie prvky

- **Enkodér:** CLK na GP12, DT na GP13; 10 nF kondenzátory slúžia na filtráciu zákmitov.
- **Tlačidlo enkodéra:** GP15, aktívne zopnutím proti GND s interným pull-up rezistorom.
- **Stavová LED:** GP14 cez 220 Ω rezistor.

## Verziovanie a vydania

Prvé označené vydanie: **v1.0.0**. Firmvér pri štarte vypisuje verziu
z Git tagu, krátke SHA, počet commitov a prípadné označenie `dirty`.
Balík na PC pripravíte z koreňa projektu:

```bash
python3 tools/prepare_firmware.py
```

V Zede možno použiť úlohu **Verzia: pripraviť firmvér** cez
Ctrl+Shift+P → `task: spawn` (na tomto PC je nastavená globálne).
Príprava vytvára `work/firmware/`; nepublikuje vydanie ani nenahráva na dosku.
Podrobný postup prípravy, prenosu a skúšky je vo
[firmware/README.md](firmware/README.md#verzia-firmvéru-z-gitu).
Zmeny vydaní sú v [CHANGELOG.md](CHANGELOG.md).

## 📄 Licencia

Tento projekt je licencovaný pod [GNU GPL v3](LICENSE).
