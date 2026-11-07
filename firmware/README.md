# Firmware

This directory contains the software running on the Raspberry Pi Pico (RP2040).

## Samostatný návod pre AI

[Podklad pre AI a dlhodobé meranie](../docs/AI_PODKLAD_DATALOGGER.md)
zhŕňa obsluhu FW 1.0.7-dev, sériové príkazy, režimy ADC, deliče,
interpretáciu CSV, obmedzenia a plánovanie experimentu. Je samostatný:
do konverzácie s AI stačí priložiť celý súbor a doplniť údaje merania.

## Hardware
- **Microcontroller:** Raspberry Pi Pico
- **Processor:** RP2040 (dual-core ARM Cortex-M0+)
- **Runtime:** MicroPython

## Development Environment
- **IDE:** Thonny
- **Language:** MicroPython

## Requirements
- Raspberry Pi Pico with MicroPython firmware installed
- Thonny IDE — [download here](https://thonny.org)

## Installation
1. Install MicroPython on the Pico:
   - Hold **BOOTSEL** button and connect Pico via USB
   - Copy the MicroPython `.uf2` file to the Pico drive
   - Pico restarts automatically
2. Open Thonny
3. Go to **Run → Select interpreter → MicroPython (Raspberry Pi Pico)**
4. Copy `.py` files to the Pico via Thonny

## Usage
- Open `main.py` in Thonny and click **Run**
- `main.py` is executed automatically on power-up

## ADS1256 input-mode menu

With logging stopped (**PAUZA**), turn the encoder to **ADS1256**, alongside
**SyncRTC** and **1WIRE**, then press the encoder button to open its submenu.
Turn toward **On** or **Off** and press again to confirm and return to PAUZA:

- **On** initializes and calibrates ADS1256 and selects AN0–AN7.
- **Off** selects the original A1/A2 and B1–B4 inputs.

Rotation only changes the highlighted choice; confirmation applies it.
The `>` cursor marks the encoder selection; `[AKT]` marks the currently
active On/Off mode, even when the cursor points elsewhere. Both ADS1256
submenus hide the clock so their titles remain fully readable.
The menu cannot be entered during REC. Stop recording first. Switching
happens immediately without restarting. A new recording uses the CSV layout
for the selected input mode. Confirmation saves On/Off to `input_mode.cfg`
in the Pico internal flash, so the choice survives power loss. Missing or
invalid settings default to **Off** (original inputs). An unchanged choice
does not rewrite flash. A temporary file is synced before replacing the
previous setting. A save failure keeps the submenu open with `Ulozenie CHYBA`;
the selected mode is active in RAM but saving must be retried.
Saved **On** attempts ADS1256 initialization at startup; an ADC failure
keeps On and reports the error without enabling the original inputs.
The averaging count is saved separately in `ads_samples.cfg`; RAW and buffer
choices use `ads_raw.cfg` and `ads_buffer.cfg`. The scrolling submenu also
contains **RAW: On/Off**, **Imp:Lo(5V)/Hi(3V)**, **Del:No/1:…** and **Spat**. See the
[mode guide](#raw-a-vstupný-buffer--105-dev) below for limits and units.
`ADS1256_VREF = 2.503` remains the measured reference setting.

Copy `input_settings.py`, `ads1256.py`, `adc_average.py` and `logger_csv.py` along with `main.py` and the existing
drivers to the Pico. Thonny is the development and upload environment.

The input configurations are mutually exclusive: GP2–GP5 and GP26/GP27
are initialized only for the selected mode. The software selection does not change external wiring or remove module
power. Use the original inputs only with the corresponding J3 wiring;
disconnect the ADS1256 before connecting original input signals.
Battery measurement on GP28/GP21, SHT4x, DS18B20, RTC and SD logging remain
available in both modes.

ADS1256 uses manual SPI with the tested 2 µs bit timing, selectable buffer (default off), PGA=1,
DRATE=0x82 (100 SPS), register verification and SELFCAL at startup.
Each scan reads AIN0–AIN7 sequentially against AINCOM, with MUX selection
and SYNC/WAKEUP before waiting for settled data. Connect AINCOM to GND
for the tested single-ended arrangement. This does not permit negative
voltages relative to GND on the inputs.
See [J3 wiring and test results](../hardware/schematic/ADS1256_J3.md) and
[TI ADS1256 datasheet](https://www.ti.com/lit/ds/symlink/ads1256.pdf).

### Averaging sample count

In PAUZA, open **ADS1256 → Vzorky**, rotate to choose **1, 2, 4, 8, 16,
or 32 samples per channel**, and press to confirm. This returns to the
ADS1256 submenu; select **Spat** to return to PAUZA. On and Off remain
available in the same submenu. Settings cannot be changed during REC.

Confirmation saves the count to `ads_samples.cfg` in internal flash and
startup restores it, including after power loss. Missing or invalid settings
default to 1 (no averaging). An unchanged count does not rewrite flash.
Saving uses the same temporary-file replacement as On/Off. A failure shows
`Ulozenie CHYBA` in the ADS1256 submenu; the count is active in RAM, and
**Vzorky** must be confirmed again to retry saving. On/Off and the count
are stored independently, so changing either preserves the other.
For an update adding this feature, deploy `input_settings.py` and `main.py`
from the freshly prepared bundle together with `build_info.py`. Back up
the existing files and configuration first. Preserve `input_mode.cfg` and
`ads_samples.cfg` on the Pico; do not replace them with PC defaults.
With **RAW Off**, for each output set, the logger takes N fresh
readings on each channel and calculates their arithmetic mean. It cycles
AN0–AN7 N times, publishing all eight averages together. Discarding an
unfinished batch on a mode or count change prevents mixed configurations.

One conversion is acquired per main-loop iteration so the encoder and
stop button remain serviced between readings. A batch requires 8 × N
iterations (at least approximately 0.4 × N seconds with the existing 50 ms
loop, plus ADC and peripheral work). A one-second pause follows each
completed batch. The ADC stays configured at 100 SPS; this is not the
rate of complete averaged output sets. More averaging trades response
time for suppression of random noise; it does not remove offset or
all interference.

The OLED cycles through AN0–AN7 on row 4, one channel every two seconds.
Row 4 also shows the waiting or error status; row 5 always shows the number
of detected 1WIRE (DS18B20) sensors (`DS: n`) while ADS1256 is enabled.
Both display
and CSV use the latest completed average, with six decimal places in volts
when **RAW Off**. **RAW On** uses one direct ADC code per channel, ignores
averaging and displays integer counts instead of volts.
If the logging interval is shorter than the averaging cycle, consecutive
CSV rows can contain the same completed average. Before the first batch
finishes, channel cells are empty and the display shows `ADS meranie...`.
CSV column names and layout are unchanged with RAW Off. The chosen sample count is
printed to Thonny Shell when confirmed.

On a read failure, the unfinished batch is discarded, all eight output
values are invalidated, and the OLED shows `ADS1256 CHYBA`. CSV then
contains empty channel cells. Subsequent batches retry. Initialization
failure can be retried by confirming **On** again. The firmware does not
fall back to conflicting original GPIO assignments.

Register verification checks only writable STATUS bits (mask `0x0E`);
bit 0 is the read-only, changing DRDY status and must not be compared to
the written configuration. A register mismatch reports its address, read
value, expected value and mask in the serial console. A `DRDY timeout`
is a separate failure, not explained by this verification check alone.

## Verification in Thonny

1. Select **Run → Select interpreter → MicroPython (Raspberry Pi Pico)**.
2. Stop the running application with **Stop/Restart backend**.
3. Upload `ads1256.py`, `adc_average.py`, `logger_csv.py` and the updated `main.py` to the
   root of **Raspberry Pi Pico** in Thonny's Files pane. Keep the existing
   peripheral drivers on the Pico.
4. Restart the board. In Shell, check the startup message confirming
   AN0–AN7 and SELFCAL OK (the default mode is On).
5. In PAUZA, rotate to ADS1256, press, select Off, and press to confirm.
   Open the submenu again, select On and confirm. Check Shell for successful
   initialization and confirm that the OLED cycles through AN0–AN7 on row 4
   while row 5 keeps showing the DS sensor count, including on ADC errors.
6. Select a 5-second recording interval. Check Shell and the new CSV file:
   AN0–AN7 must be present and A1/A2/BIN absent. Battery and temperature
   readings must remain. While REC is active, rotation must not open the
   input-mode menu; pressing the button stops recording.
7. With suitable original-input wiring, repeat a recording with Off selected
   and verify that the original CSV columns return. Each mode change must
   happen while recording is stopped.

8. In PAUZA, select ADS1256 → Vzorky. Compare 1 and 8 samples per channel
   on a stable input, allowing each batch to finish. Check averaged display
   and CSV values, slower refresh, and stop-button response during collection.

## Measured Parameters
- SHT4x temperature and relative humidity
- Multiple DS18B20 temperature sensors
- Eight ADS1256 inputs AN0–AN7, or two original analog voltage inputs
- Battery voltage
- Four digital inputs in the original input mode

## Data Output
- CSV logging to microSD card
- Serial diagnostic output over USB
- Measurement status on SSD1306 OLED
- Logging interval selectable from 5 to 300 seconds
- CSV files use the timestamp format `YYYYMMDD_HHMMSS.csv`

## Operating Modes

The logger is controlled using the rotary encoder and its push button.

- **PAUZA** — measurements are displayed, but data is not written to the SD card.
- **REC** — measurements are periodically written to a CSV file.
- **1WIRE** — displays connected DS18B20 sensors, their ROM IDs and temperatures.
- **SYNC** — synchronizes the external DS3231 RTC with the current internal RTC time.

While in PAUZA mode, the rotary encoder selects `Restart`, `SyncRTC`, `ADS1256`,
`1WIRE`, or a logging interval from 5 to 300 seconds in 5-second steps.
Pressing the encoder on `Restart` synchronizes the filesystem and resets
the Pico, starting the application again. Restart is unavailable during REC.

## CSV Format

Each recording creates a new timestamped CSV file.

With ADS1256 **Off**, the fixed columns are:

```text
Cas,SHT_T,SHT_H,A1,A2,BAT,BIN,B1,B2,B3,B4
```

With ADS1256 **On** and **RAW Off**, they are:

```text
Cas,SHT_T,SHT_H,AN0,AN1,AN2,AN3,AN4,AN5,AN6,AN7,BAT
```

With ADS1256 **On** and **RAW On**, they are:

```text
Cas,SHT_T,SHT_H,AN0_RAW,AN1_RAW,AN2_RAW,AN3_RAW,AN4_RAW,AN5_RAW,AN6_RAW,AN7_RAW,BAT
```

RAW changes only the eight ADS1256 columns; temperatures, humidity and
battery stay in their original units. Lo/Hi and averaging count are not
stored as CSV metadata; note these settings and the divider separately when
comparing files. Since 1.0.6-dev, AN0–AN7 contain the reconstructed voltage
before the divider when Del is enabled; RAW codes remain unchanged.

The ROM ID of each detected DS18B20 sensor is appended to the header as an
additional column.

An example recording is available in `../docs/data/`.

## Firmware Files

| File | Description |
|---|---|
| `main.py` | Main application, encoder input-mode menu and measurement loop |
| `ads1256.py` | J3 ADS1256 driver, eight single-ended inputs |
| `adc_average.py` | Incremental eight-channel arithmetic averaging |
| `logger_csv.py` | CSV header and row formatting for both input modes |
| `ds3231.py` | DS3231 RTC driver |
| `sdcard.py` | microSD card driver |
| `sht4x.py` | SHT4x temperature/humidity driver |
| `ssd1306.py` | SSD1306 OLED driver |
| `TimeSet.py` | RTC utility |
| `TimeSyncPC.py` | RTC synchronization utility |

## Development Status

The battery measurement circuit and the corresponding firmware are still
under development and may change.

The integrated ADS1256 firmware has passed host-side simulated checks.
On 2026-10-19, the user confirmed that ADS1256 On/Off switching through
the rotary-encoder menu works on the Pico. This confirms the hardware
check of the input-mode switch; it does not constitute a new verification
of ADC accuracy, CSV contents, or fault handling.

The sample-count submenu and averaging added after the On/Off hardware
check have passed host-side tests; Pico verification of this addition is pending.


## Verzia firmvéru z Gitu

Podobne ako ESP32 prehrávač používa datalogger najbližší dosiahnuteľný
Git tag `vMAJOR.MINOR.PATCH` (prípadne bez `v`), krátke SHA commitu a počet
commitov v histórii HEAD. Bez tagu sa používa `0.0.0-dev`. Medzi vydaniami
zostáva verzia posledného tagu, ale SHA a číslo zostavenia sa menia.
`dirty` znamená, že pri príprave boli prítomné necommitnuté zmeny alebo
nesledované súbory. Neoznačuje presný obsah týchto zmien.

MicroPython nemá krok kompilácie PlatformIO, preto balík pripravujeme na PC
z koreňa projektu:

```bash
python3 tools/prepare_firmware.py
```

Výstup je v `work/firmware/`: kópie Python súborov z `firmware/` a generovaný
`build_info.py`. Príprava nenahráva nič na Pico, nemení zdrojové súbory ani
nevytvára Git tag. Pri opakovaní prepíše iba generovaný priečinok
`work/firmware/`; neukladajte doň ručné úpravy ani zálohy.

Na Pico prenášajte zodpovedajúce zmenené aplikačné súbory z tohto balíka
spolu s `build_info.py`. Pred prenosom zastavte REC do PAUZA, overte port
a zálohujte dotknuté súbory z dosky. Zmenené ovládače a ich závislosti
preneste spolu s aplikáciou; nespúšťajte automaticky pomocné TimeSet/TimeSyncPC.
Nevykonávajte hromadné mazanie obsahu Pico ani SD karty.

Pri zavedení verziovania sú nové `main.py` a `build_info.py`. Po overení
portu a zálohe ich možno preniesť takto (pri zmene iných modulov pridajte aj tie):

```bash
mpremote connect /dev/ttyACM0 fs cp work/firmware/build_info.py work/firmware/main.py :
```

Tento príkaz zastaví program a prepíše oba súbory; spustite ho iba pri
zamýšľanom nasadení na konkrétne Pico. Pre spoľahlivé zachytenie štartovacieho výpisu otvorte konzolu:

```bash
mpremote connect /dev/ttyACM0 repl
```

V konzole stlačte Ctrl-C na prerušenie prípadného programu a potom Ctrl-D
na softvérový reštart a spustenie `main.py`. Záznam musí byť predtým
zastavený v PAUZA. Samotné `soft-reset repl` môže ponechať dosku v konzole
bez spustenia aplikácie; vtedy tiež použite Ctrl-D.
REPL ukončíte Ctrl-X. Pri štarte sa vypíše napríklad:

```text
[BUILD INFO] version=1.0.0 git=12345678 build=42
```

Samotné metadáta nedokazujú zhodu všetkých súborov na doske s Gitom.
Pri ručnom kopírovaní pôvodného `firmware/main.py` bez `build_info.py`
funguje aplikácia s verziou `0.0.0-dev`, SHA `unknown` a číslom `0`.
Starý `build_info.py` však zostane starý: pred každým nasadením znovu
pripravte balík a preneste aj čerstvé metadáta.

### Vydanie novej verzie

Najprv otestujte zmeny a vytvorte commit so zamýšľanými súbormi. Potom
vytvorte anotovaný tag, napríklad `git tag -a v1.0.0 -m "Version 1.0.0"`,
a znovu pripravte balík. Prvé vydanie tohto projektu je `v1.0.0`;
pri ďalšom vydaní zvoľte nové číslo, existujúci tag znovu nevytvárajte.
Tag vzniká lokálne; jeho publikovanie vyžaduje samostatný push. Tagy
vydaných verzií spätne nepresúvajte. Do commitov nepatria `.venv/`, `work/`
ani generovaný `build_info.py`. Pri prázdnej alebo shallow histórii je
potrebné najprv zabezpečiť úplnú históriu a tagy pre správne číslovanie.

Overenie na PC: `python3 -m unittest discover -s firmware/tests`.
Výpis verzie ani úspešný PC test nenahrádzajú skúšku na fyzickom Pico.


### Jednoduchá úloha v Zede

#### Typové definície MicroPythonu pre Pico

Projektový `pyrightconfig.json` nastavuje kontrolu firmvéru v Zede
(basedpyright/Pyright) pomocou stubs pre **RP2040 / Raspberry Pi Pico,
MicroPython 1.27.0**. Definície sú iba na PC v ignorovanom priečinku
`work/micropython-stubs`; nekopírujú sa na Pico a nemenia beh programu.
Inštalácia z koreňa projektu do existujúceho virtuálneho prostredia:

```bash
.venv/bin/python -m pip install --no-user --target work/micropython-stubs -r requirements-stubs.txt
```

Verzie balíkov sú pevne určené v `requirements-stubs.txt`. Po inštalácii
v Zede použite Ctrl+Shift+P → `editor: restart language server`, ak sa
diagnostika neobnoví automaticky. Funkcie `time.ticks_diff`, `ticks_ms`,
`sleep_ms` a modul `machine` sa tak kontrolujú podľa MicroPythonu.
Upozornenie na chýbajúci Python zdroj natívnych modulov je vypnuté;
kontrola chýbajúcich atribútov a importov zostáva zapnutá.

Projektová kontrola zahŕňa firmvér, nie PC testy v `firmware/tests` ani
nástroje v `tools`. Stubs nie sú nainštalované do `.venv` ako runtime moduly.
Existujúce testy sa naďalej spúšťajú bežným Pythonom. Ostatné diagnostické
hlásenia môžu zostať: stubs nenahrádzajú skúšku na hardvéri a nemusia
opisovať všetky staršie aliasy dostupné na skúšanej doske.

#### Príprava balíka

Na aktuálnom Linux PC je v globálnom `~/.config/zed/tasks.json` úloha
**Verzia: pripraviť firmvér**. Spustenie: Ctrl+Shift+P → `task: spawn` →
vybrať názov úlohy. Pred spustením uloží otvorené upravené súbory a
v koreňovom priečinku aktuálneho projektu zavolá
`python3 tools/prepare_firmware.py`. Nerobí commit, tag, upload ani push.

Globálna úloha platí aj v ďalších projektoch, ale tie musia poskytovať
vlastný `tools/prepare_firmware.py`. Samotná úloha do nich verziovanie
nepridáva. Nový MicroPython projekt musí mať vhodnú štruktúru `firmware/`,
Git repozitár, ignorovaný `/work/` a aplikáciu čítajúcu generované metadáta.
Pri PlatformIO projekte ako prehrávač sa verzie generujú počas `pio run`.
Na inom PC treba preniesť aj globálne nastavenie úlohy; na Windows použiť
príkaz `python`, ak `python3` nie je dostupný. Projektová alternatíva je
`.zed/tasks.json`, ktorá sa môže uložiť do repozitára.


### Overenie verziovania na Pico – 24. 10. 2026

Používateľ overil spustenie globálnej úlohy v Zede. Pred nahraním bol
z dosky zálohovaný `main.py` do `work/pico-before-versioning/main.py`.
Po prenose `main.py` a `build_info.py` a reštarte cez Ctrl-D doska vypísala:

```text
[BUILD INFO] version=0.0.0-dev git=dbf0b39d build=66 dirty
Vstupy: ADS1256 AN0-AN7, VREF=2.503 V, PGA=1, 100 SPS, SELFCAL OK
SD karta pripravena.
```

Používateľ potvrdil funkčný displej aj ovládanie dataloggera. Toto je
hardvérová skúška zavedenia verziovania na Pico s MicroPython 1.27.0,
nie nové overenie presnosti ADC, obsahu CSV ani všetkých režimov priemerovania.

Overený bol vývojový balík pred vytvorením vydávacieho commitu. Po vytvorení
tagu `v1.0.0` treba znovu pripraviť a podľa potreby nasadiť balík s novými
metadátami. Existujúce údaje na doske sa vytvorením tagu automaticky nemenia.


## Štartovacie logo a verzia

Po inicializácii OLED SSD1306 (128 × 64) sa približne na 2 sekundy zobrazí
logo MultiChannel Datalogger. Potom sa vymaže a aplikácia pokračuje
inicializáciou periférií a bežným zobrazením. Pauza je iba pri štarte,
nie v meracej slučke ani počas REC.

Obrázok v `firmware/logo.py` je nemenný 1-bitový podklad od používateľa.
Verzia sa vykreslí zvlášť, vpravo dole z `BUILD_VERSION` načítanej
z generovaného `build_info.py`. Pri ďalšom vydaní netreba meniť logo.
Vývojová verzia sa zobrazuje ako `v0.0.0-dev`; úplné SHA, číslo a dirty
zostávajú v sériovom výpise. Text dlhší než 15 znakov sa na OLED skráti
s koncovým `~`, aby nezasahoval do rámika; sériový výpis ostáva úplný.

Balík pripravte úlohou Zedu alebo `python3 tools/prepare_firmware.py`.
Pri prvom nasadení tejto funkcie treba po zastavení REC a zálohe preniesť
**`logo.py`, `main.py` a čerstvý `build_info.py`** z `work/firmware/` na Pico.
Samotný PNG obrázok na doske netreba. Podklady sú uložené v `docs/logo/`.

PC testy overujú rozmery bitmapy, dynamické umiestnenie verzie a časovanie
s náhradou displeja. Dňa 24. 10. 2026 používateľ na fyzickom Pico potvrdil
zobrazenie loga s `v1.0.0` približne na dve sekundy a následný návrat na
bežnú obrazovku dataloggera. Pred nahratím boli zálohované `main.py` a
`build_info.py`; obsah troch prenesených súborov bol overený spätným načítaním.
Testovaný balík hlásil commit `82f419ad`, zostavenie `67 dirty`, teda zmeny
štartovacej obrazovky ešte neboli commitnuté. Nejde o nové vydanie v1.0.0.

## Ukladanie počtu vzoriek – v1.0.4, 25. 10. 2026

Verzia v1.0.4 dopĺňa trvalé uloženie počtu vzoriek na kanál (1, 2, 4, 8,
16 alebo 32) pri potvrdení **ADS1256 → Vzorky**. Po štarte sa obnoví uložená
hodnota; bez platného súboru sa použije 1. Voľba On/Off zostáva samostatná.
Pri zmene počtu sa rozpracovaná dávka aj staré výsledky zahodia.

Na PC prešlo 25 testov vrátane načítania, validácie, vynechania opakovaného
zápisu, chýb uloženia a zrušenia rozpracovanej dávky. Na Pico s MicroPython
1.27.0 bol overený zápis a načítanie hodnoty 32 v skúšobnom súbore; pôvodné
nastavenie On/1 zostalo zachované. Používateľ následne potvrdil overenie
uchovania počtu vzoriek po odpojení napájania na vývojovom balíku
`1.0.3`, commit `4d9935ad`, zostavenie `70 dirty`, pred vydaním v1.0.4.

Toto overenie nepotvrdzuje presnosť ani spoľahlivosť komunikácie ADS1256.
Pri poslednom štarte tohto vývojového balíka sa objavil `ADS1256 DRDY timeout`;
SD karta bola pripravená. Chybu komunikácie treba posudzovať samostatne.


## RAW a vstupný buffer – 1.0.5-dev

V menu **ADS1256** pribudli prepínače **RAW: On/Off** a
**Imp:Lo(5V)/Hi(3V)**. Otáčaním sa posúva zoznam, stlačením sa prepne
hodnota. Menu je dostupné iba zo STOP/PAUZA; počas REC sa konfigurácia
nemení. Obe voľby sa uchovajú po vypnutí napájania (`ads_raw.cfg`,
`ads_buffer.cfg`). Bez platného nastavenia platí RAW Off a Imp:Lo(5V).
Pri zmene sa zahodia staré výsledky aj rozpracovaná dávka; pri zmene
bufferu sa ADC inicializuje a kalibruje znova. Chyba uloženia sa zobrazí
ako `Ulozenie CHYBA`; zvolená hodnota vtedy platí len v RAM.

- **RAW On:** priame podpísané 24-bitové kódy −8388608 až 8388607,
  bez prepočtu na volty a bez priemerovania (jedna čerstvá vzorka/kanál).
  CSV má stĺpce `AN0_RAW` až `AN7_RAW` s celými číslami; ostatné stĺpce
  sa nemenia. OLED zobrazuje `RAW0:` až `RAW7:`. Pri chybe zostávajú bunky
  prázdne. Každé spustenie REC vytvorí nový súbor, takže jednotky sa nemiešajú.
  Uložený počet vzoriek sa zachová a opäť sa používa po RAW Off.
- **RAW Off:** pôvodný CSV formát `AN0` až `AN7` vo voltoch s priemerovaním.
- **Imp:Lo(5V):** BUFEN=0, vstupný buffer vypnutý (pôvodné správanie).
- **Imp:Hi(3V):** BUFEN=1, vstupný buffer zapnutý. Podľa
  [TI datasheetu](https://www.ti.com/document-viewer/ADS1256/datasheet)
  musia byť všetky použité analógové vstupy vrátane AINCOM v rozsahu
  AGND až AVDD − 2 V, teda približne 0–3 V pri AVDD=5 V.
  Zapnutie bufferu nezväčšuje povolený napäťový rozsah.

Pri aktuálnom PGA=1, DRATE=100 SPS a hodinách ADC 7,68 MHz je podľa
TI typická efektívna diferenciálna vstupná impedancia približne **150 kΩ
pri Lo** (buffer off) a **40 MΩ pri Hi** (buffer on, tabuľka 3 datasheetu).
Hodnota 80 MΩ sa pri zapnutom bufferi vzťahuje na rýchlosti do 50 SPS,
nie na aktuálnych 100 SPS. Ide o parametre ADC, nie zmeranú impedanciu
celého modulu. Údaje 5V/3V v menu predpokladajú AVDD=5 V a AINCOM=GND.

### Prehľad režimov pri práci

Nasledujúce rozsahy platia pre vstupy AN0–AN7 pri AINCOM=GND, AVDD=5 V,
PGA=1 a referencii 2,503 V. RAW a impedancia sú nezávislé voľby:

| RAW | Imp | Napätie vstupu voči GND | Typická impedancia ADC | Výsledok |
| --- | --- | --- | --- | --- |
| Off | Lo(5V) | približne 0–5 V | 150 kΩ | volty, priemer N vzoriek |
| Off | Hi(3V) | 0–3 V | 40 MΩ | volty, priemer N vzoriek |
| On | Lo(5V) | približne 0–5 V | 150 kΩ | priamy celočíselný kód, N=1 |
| On | Hi(3V) | 0–3 V | 40 MΩ | priamy celočíselný kód, N=1 |

Lo je vhodné pre zdroje s malým výstupným odporom. Hi menej zaťažuje zdroj,
ale vyžaduje menší napäťový rozsah. Napríklad ideálny zdroj s výstupným
odporom 10 kΩ má pri jednoduchom odporovom modeli ADC v Lo zaťažením
chybu približne 6,25 %, v Hi približne 0,025 %. Je to orientačný výpočet
zaťaženia, nie celková chyba merania ani hardvérové overenie modulu.

Údaj 5V/3V v menu je pripomienka rozsahu pri 5 V napájaní, nemení zosilnenie
ani napájanie ADC. Pre Hi všeobecne platí horná hranica AVDD − 2 V.
Napríklad pri AVDD=4,8 V je to iba 2,8 V. Pre Lo držte signál v rozsahu
GND až AVDD a zároveň v rozsahu prevodníka. Diferenciálny plný rozsah je
±2 × VREF/PGA = ±5,006 V, ale jednotlivé piny stále musia spĺňať svoje
napäťové obmedzenia; pri AINCOM na GND to neumožňuje priviesť −5 V.
RAW tieto hranice nemení. Záporný RAW kód blízko nuly môže vzniknúť
šumom alebo offsetom; nie je povolením merať záporné napätie voči GND.

Prepočet pri aktuálnej konfigurácii je
`U = RAW × (2 × 2,503 / 8388607)` V; jeden kód predstavuje približne
0,597 µV. Krok kódu nie je presnosť merania. Aj v režime RAW zostáva
aktívna interná kalibrácia ADC; obchádza sa prepočet a priemerovanie
v aplikácii, nie vnútorné spracovanie prevodníka.

**Vzorky** uchováva N=1, 2, 4, 8, 16 alebo 32. V RAW On sa efektívne
používa iba N=1 a podmenu upozorňuje `RAW pouziva N=1`. Po RAW Off sa
obnoví použitie uloženého N. AN0–AN7 sa čítajú postupne, nie súčasne.
100 SPS je nastavenie ADC, nie počet úplných osemkanálových sád za sekundu;
ani pomalšie ukladanie CSV, ani väčšie N nemení impedanciu ADC na 80 MΩ.

Zmena RAW alebo Imp zruší rozpracovanú dávku aj staré hodnoty a pri
zapnutom ADS znovu inicializuje a kalibruje ADC. Pri ADS Off sa nastavenia
uchovajú pre ďalšie zapnutie ADS, pôvodné vstupy sa nimi nemenia.
On/Off vracia do PAUZA; prepnutie RAW/Imp ponechá otvorené menu.
Z ponuky sa vrátite cez **Spat**. Nastavovať možno iba pri zastavenom REC.

Ak uloženie prepínača zlyhá, hodnota platí v RAM a zobrazí sa
`Ulozenie CHYBA`. Odstráňte príčinu chyby a overte uloženie požadovanej
hodnoty; každé stlačenie RAW/Imp hodnotu znovu **prepne**. Na opakovanie
uloženia rovnakej hodnoty treba prepnúť na opačnú a potom späť. Pri chybe
inicializácie sa ADS nevypne automaticky; zopakujte inicializáciu cez On.
Chyba čítania zneplatní celú sadu a CSV má prázdne bunky, nie nuly.
Pred prvou úplnou sadou sú bunky tiež prázdne. Ak je záznam rýchlejší
než dokončovanie sád, CSV môže opakovať poslednú dokončenú sadu aj v RAW.

### Príprava a overenie

Príprava tohto vývojového balíka bez vytvárania Git tagu:
`python3 tools/prepare_firmware.py --version 1.0.5-dev`.
Voľba `--version` povoľuje iba vývojové verzie `X.Y.Z-dev`; SHA, číslo
zostavenia a dirty sa stále získavajú z Gitu. Bez tejto voľby naďalej
platí verzia odvodená z tagov. Ide o MicroPython zdroje, nie nový UF2.
Po zastavení záznamu a zálohe dotknutých súborov z Pico sa prenášajú iba
`main.py`, `ads1256.py`, `adc_average.py`, `input_settings.py`,
`logger_csv.py` a čerstvý `build_info.py` z `work/firmware/`.

Na Pico treba overiť posúvanie menu, oba prepínače, uchovanie po reštarte,
RAW CSV vrátane záporných hodnôt a návrat na volty s pôvodným počtom
vzoriek. Analógovú presnosť a vhodnosť vysokého vstupného odporu treba
preveriť so zapojeným zdrojom signálu v povolenom rozsahu.

Overenie tejto úpravy na PC: 32 testov prešlo vrátane podpísaných RAW
kódov, BUFEN a kalibrácie, RAW CSV, uloženia nastavení, resetu dávky
pri prepnutí a identifikácie vývojového balíka. Nasadenie na Pico prebehlo 4. 11. 2026 po potvrdení STOP/PAUZA.
Záloha šiestich prepísaných súborov a pôvodných nastavení je v
`work/pico-before-raw-buffer-20261104/` (nejde o zálohu SD karty).
Spätné načítanie potvrdilo presnú zhodu všetkých šiestich súborov s balíkom;
kompilácia zdrojov na Pico overila syntax v MicroPythone 1.27.0.
Po soft reštarte aplikácia hlásila `1.0.5-dev`, Git `32323837`, build
`71 dirty`, úspešnú inicializáciu a SELFCAL ADC a pripravenú SD kartu.
Nastavenie ADS On / 8 vzoriek zostalo zachované, nové voľby mali predvolené
hodnoty RAW Off / Vstup Nizko. Štartový výpis je uložený v
`work/pico-verify-raw-buffer-20261104/startup.txt`.
Fyzické ovládanie nových položiek, RAW záznam na SD, uchovanie nových
volieb po vypnutí napájania a meranie s bufferom tým neboli overené.


### Nasadenie označenia Imp:Lo(5V)/Hi(3V) – 4. 11. 2026

Po potvrdení STOP používateľom bol na Pico nahratý aktuálny balík
`1.0.5-dev`, Git `32323837`, build `71 dirty`. Pred prenosom boli zálohované
všetky jeho súbory (`main.py`, `build_info.py`, `ads1256.py`, `adc_average.py`,
`input_settings.py`, `logger_csv.py`) do
`work/pico-before-imp-voltage-label-20261104/`. Zmenil sa text menu v
`main.py`; ostatné súbory už zodpovedali pripravenému balíku. Dokumentácia
zostáva v repozitári, nekopírovala sa na Pico ani na SD.

SHA-256 všetkých šiestich súborov na doske sa zhodovalo s balíkom.
Kompilácia `main.py` na doske overila syntax. Nastavenia zostali ADS On,
8 vzoriek, RAW Off a Imp Lo. Po soft reštarte bol potvrdený úspešný SELFCAL
ADC aj pripravená SD karta, bez chyby v zachytenom štartovom výpise.
Protokoly `verification-after.txt` a `startup-after.txt` sú v priečinku
zálohy. Posledný PC beh nezmeneného firmvéru mal 32 úspešných testov.
Na displeji treba ešte potvrdiť nové označenie; všetky kombinácie režimov,
CSV na SD, presnosť a uchovanie nových volieb po odpojení napájania
neboli týmto nasadením otestované.


## Vstupný delič – 1.0.6-dev

**ADS1256 → Del:No / Del:1:xxxxx** nastavuje jeden spoločný prepočet pre
všetky AN0–AN7. Predpokladá rovnaký samostatný fyzický delič na každom
použitom kanáli. Nastavenie nepripája rezistory, nemení GPIO ani pôvodné
vstupy A1/A2 pri ADS Off. Bez platného `ads_divider.cfg` sa použije **No**.
Číselné hodnoty pripravené v editore sú Rgnd=10000 Ω a Rin=90000 Ω,
ale tento delič sa bez potvrdenia **Pouzit** nepoužíva.

### Zapojenie a výpočet

```text
Merané Uin ── Rin ──┬── ANx (vstup ADC)
                    │
                   Rgnd
                    │
GND ────────────────┴── AINCOM
```

Rgnd je dolný odpor proti GND; Rin je horný sériový odpor od meraného
napätia k ANx. Oba sa zadávajú v celých ohmoch, Rgnd od 1 do 99999999 Ω,
Rin od 0 do 99999999 Ω. Rgnd=0 editor nepovolí potvrdiť. Rin=0 je
prípustné priame pripojenie (prevod 1); nezväčšuje rozsah.

Pre aktuálne PGA=1, 100 SPS a CLKIN=7,68 MHz model používa typickú
impedanciu ADC **Zadc=150000 Ω v Lo** alebo **40000000 Ω v Hi**.
Zdroj: [TI ADS1256 datasheet, elektrické parametre a tabuľka 3](https://www.ti.com/document-viewer/ADS1256/datasheet).
Keďže Zadc zaťažuje dolný odpor, výpočet je:

```text
Rd = Rgnd || Zadc = 1 / (1/Rgnd + 1/Zadc)
K  = 1 + Rin/Rd = 1 + Rin/Rgnd + Rin/Zadc
Uin = Uadc × K
```

Menu ukazuje pomer **Uadc:Uin = 1:K**; pri No je K=1. Koeficient sa
počíta z odporov s plnou dostupnou presnosťou MicroPythonu, nezaokrúhľuje
sa na skrátený text menu. Zmena Imp automaticky zmení koeficient aj rozsah.

Pri nominálnom AVDD=5 V, AINCOM=GND, PGA=1 a VREF=2,503 V:

| Rgnd | Rin | Imp | K | Vypočítaný rozsah Uin |
| --- | --- | --- | --- | --- |
| bez deliča (No) | — | Lo | 1 | približne 0–5 V |
| bez deliča (No) | — | Hi | 1 | približne 0–3 V |
| 10000 Ω | 90000 Ω | Lo | 10,6 | približne 0–53 V |
| 10000 Ω | 90000 Ω | Hi | 10,00225 | približne 0–30,00675 V |

Výpočet horného rozsahu je `K × min(Ulimit, 2 × VREF)`, kde Ulimit je
AVDD v Lo a AVDD−2 V v Hi. `ADS1256_AVDD=5.0` je nominálna konštanta,
nie priebežné meranie napájania. Napätie na ANx musí stále zostať vo svojom
rozsahu; delič nemení povolené napätie na pine ADC. Uvedený rozsah je
výsledok odporového modelu, nie overenie napäťovej alebo výkonovej
zaťažiteľnosti rezistorov, modulu a ostatného zapojenia.

Kompenzácia používa typickú, nie individuálne zmeranú impedanciu ADC.
Nezahŕňa tolerancie rezistorov, výstupný odpor zdroja, ďalšie súčiastky
modulu ani dynamické ustálenie po prepnutí kanála. Preto po nastavení
odporov treba prevod preveriť známym napätím; nejde o kalibráciu presnosti.

### Ovládanie enkodérom

1. Zastavte REC, v STOP/PAUZA otvorte **ADS1256 → Del**.
2. Vyberte **Rgnd** alebo **Rin**. Otočenie mení podčiarknutú číslicu
   0–9, stlačenie posunie kurzor doprava. Zadáva sa osem číslic s úvodnými
   nulami, napr. `00010000` = 10000 Ω. Posledné stlačenie vráti do podmenu.
3. **Prevod/rozsah** ukáže zadané odpory, navrhovaný K a rozsah pred
   deličom pri aktuálnom Imp. Spodný riadok **Akt:0-…V** ukazuje rozsah
   aktuálne používaného nastavenia pri vstupe do editora. Náhľad predpokladá
   zapnutie zadaného deliča aj vtedy, keď je zatiaľ aktívne No. Stlačenie
   vráti do podmenu; otáčanie v náhľade nič nemení.
4. **Pouzit** zapne zadaný delič a uloží nastavenia; **No** vypne prepočet
   a uloží voľbu, odpory zostanú zapamätané. **Spat** zahodí rozpracované
   zmeny. Všetky tri voľby vrátia do menu ADS1256; jeho **Spat** do PAUZA.

Pri editovaní pokračuje meranie s pôvodným nastavením. Až **Pouzit/No**
zruší staré výsledky a rozpracovanú dávku; začína sa nová čerstvá sada.
Počas REC nie je menu ani úprava dostupná. Súbor `ads_divider.cfg` v internej
flash uchová spolu On/Off, Rgnd a Rin cez dočasný súbor a synchronizáciu;
opakované uloženie rovnakého nastavenia flash neprepisuje. Pri chybe zápisu
platí zvolená hodnota v RAM a menu hlási `Ulozenie CHYBA`. Na opakovanie
uloženia znovu otvorte Del a potvrďte Pouzit alebo No podľa požadovanej voľby.

### Výstupné hodnoty, RAW a priemerovanie

- **RAW Off, Del No:** pôvodné napätie ADC, vo voltoch.
- **RAW Off, Del 1:K:** všetkých osem hotových priemerov sa vynásobí K
  jedenkrát. OLED, sériový výpis aj CSV `AN0`–`AN7` obsahujú Uin pred
  deličom, vo voltoch. Počet vzoriek a šesť desatinných miest CSV ostávajú.
  Dlhé napätie na OLED sa zobrazí so skrátenou presnosťou alebo exponentom,
  aby sa zmestilo do riadka; CSV používa šesť desatinných miest.
- **RAW On:** CSV `AN0_RAW`–`AN7_RAW` zostávajú priame podpísané kódy ADC,
  bez deličového prepočtu a bez priemerovania. Nastavený delič sa uchová
  pre návrat do RAW Off. Rozsah v náhľade stále označuje fyzické Uin, nie
  rozsah celočíselných kódov. Ručný prepočet je
  `Uin = RAW × (2 × 2,503 / 8388607) × K`.
- Chýbajúca alebo chybná sada má stále prázdne CSV bunky. Hlavičky,
  ostatné senzory, batéria a vytváranie nových súborov sa nemenia.
  CSV neukladá odpory ani K ako metadáta; pri porovnávaní si zapíšte režim
  Imp a hodnoty deliča samostatne. Po zmene konfigurácie začnite nový REC.

### Balík a overenie

Verzia tohto vývojového balíka je **1.0.6-dev**, bez nového Git tagu.
Pred nasadením pripravte zdroje a čerstvé metadáta príkazom:

```bash
python3 tools/prepare_firmware.py --version 1.0.6-dev
```

Nový modul **`adc_divider.py`** treba preniesť spolu s upravenými
**`main.py`**, **`input_settings.py`** a čerstvým **`build_info.py`**
z `work/firmware/`. Ostatné ADS moduly musia zodpovedať aktuálnemu balíku.
Pred nahratím zastavte záznam a zálohujte prepisované súbory z konkrétneho
Pico. Existujúce `.cfg` neprepisujte predvolenými súbormi z PC.

Všetkých **42 PC testov prešlo**. Testy overujú zaťažený delič v Lo/Hi,
výpočet rozsahu, No a RAW,
validáciu a uchovanie nastavení pri chybe, editovanie po čísliciach,
rozmery textov OLED, zahodenie dávky a prepočet pred zápisom CSV.
Na Pico zostáva preveriť ovládanie, uloženie po odpojení napájania,
CSV vo všetkých kombináciách a prevod známym napätím. Priebeh nasadenia je zaznamenaný nižšie; fyzické ovládanie a presnosť
prepočtu deliča ešte neboli overené.


### Nasadenie deliča na Pico – 5. 11. 2026

Po potvrdení STOP bol na Pico RP2040 s MicroPythonom 1.27.0 nahratý
balík `1.0.6-dev`, Git `32323837`, build `71 dirty`. Záloha šiestich
existujúcich súborov balíka a troch existujúcich `.cfg` je v
`work/pico-before-divider-20261105/`. Nejde o zálohu SD karty.
Prenesené boli `main.py`, `input_settings.py`, nový `adc_divider.py`
a aktuálny `build_info.py`; ostatné tri ADS moduly sa už zhodovali s balíkom.
Existujúce nastavenia neboli prepísané a `ads_divider.cfg` ešte nevznikol.

Po vyčistení starých importovaných modulov soft resetom sa overila zhoda
SHA-256 všetkých siedmich súborov, syntax, výpočet prevodu v Lo/Hi a
formátovanie obrazoviek deliča priamo v MicroPythone, s náhradou displeja.
Zachované boli ADS On, 8 vzoriek, RAW Off, Imp Lo; chýbajúce nastavenie
deliča sa správne načítalo ako No s pripravenými odpormi 10000/90000 Ω.
Následný štart aplikácie potvrdil verziu 1.0.6-dev, SELFCAL OK a pripravenú
SD kartu. Protokoly `verification-after.txt` a `startup-after.txt` sú
v priečinku zálohy. Ovládanie fyzickým enkodérom, zápis záznamu s deličom,
uchovanie jeho nastavení po odpojení napájania a analógová presnosť
neboli touto kontrolou overené.


## Sériové ovládanie – 1.0.7-dev

USB konzola Pico (`/dev/ttyACM…` na Linuxe) počas behu aplikácie prijíma
**START, STOP, STATUS, HELP a RESET**. Ide o USB CDC konzolu MicroPythonu,
nie nový hardvérový UART na GPIO. Nastavenia zostávajú výhradne v menu.
Príkazy sú neblokujúco čítané cez
[`select.poll(0)` v MicroPythone 1.27.0](https://docs.micropython.org/en/v1.27.0/library/select.html).

Použite sériový terminál, napr. s rýchlosťou 115200, a príkaz odošlite
s Enter (LF, CR alebo CRLF). Malé/veľké písmená nerozhodujú, okrajové
medzery sa ignorujú. Nepoužívajte príkazy na vstup do REPL ani automatický
reset pri pripojení; `mpremote exec` nie je spôsob odoslania aplikačného
príkazu a bežiacu aplikáciu preruší. Port nesmie súčasne používať druhý
terminál alebo IDE. Ctrl-C stále preruší celý program a Ctrl-D v REPL
vykoná soft reštart; nenahrádzajú aplikačný STOP/START.

| Príkaz | Správanie |
| --- | --- |
| `START` | Z PAUZA spustí REC s intervalom zvoleným v menu (5–300 s). Vyhľadá DS senzory, zvolí názov nového CSV a spustí časovanie. |
| `STOP` | Z REC prejde do PAUZA. Zastaví zápis, ale meranie a zobrazovanie naďalej pokračujú ako doteraz. |
| `STATUS` | Vypíše aktuálny režim a konfiguráciu bez ich zmeny. |
| `HELP` | Vypíše príkazy, použitie a obmedzenia. |
| `RESET` | Iba v PAUZA synchronizuje úložisko a reštartuje Pico, čím sa znovu spustí firmvér. |

START počas REC iba oznámi `already REC` a nemení názov súboru ani časovanie.
STOP mimo REC iba potvrdí `already stopped`; neopustí TEST ani menu,
nezahodí jeho rozpracované nastavenia. START v menu/TEST/SYNC je odmietnutý.
Ak je v PAUZA vybrané Restart, SyncRTC, ADS1256 alebo 1WIRE namiesto
číselného intervalu, START sa odmietne tiež: enkodérom najprv zvoľte
interval 5–300 s. Príkaz START neprijíma interval ako argument.

Po prvom START sa prvý riadok CSV zapíše až po uplynutí zvoleného intervalu,
nie okamžite. Chýbajúca SD alebo chyba ADC naďalej neblokujú spustenie REC,
rovnako ako pri tlačidle. STATUS upozorní na nedostupnú SD alebo chybu ADC;
chybná ADS sada sa zapisuje ako prázdne bunky podľa pôvodného správania.
STOP je obslúžený medzi iteráciami slučky, nie uprostred prebiehajúceho
čítania ADC alebo SD zápisu. Súbory sú pri každom zápise uzatvorené,
flushnuté a synchronizované pôvodným postupom. Protokol nezavádza nové
nastavenia, zmeny CSV schémy ani zápis `.cfg`.

RESET sa počas REC odmietne: najprv pošlite STOP a počkajte na potvrdenie
PAUZA. V menu alebo TEST sa RESET tiež odmietne; najprv ich opustite
ovládaním na doske. Reset zruší neuložený stav v RAM a po štarte načíta
uložené nastavenia, nevykoná obnovu predvolených nastavení ani nespustí REC.
Pri chybe `uos.sync()` sa nevykoná. Odpoveď `[OK] RESET restarting firmware`
sa odošle pred resetom, ale vzhľadom na reset USB ju terminál nemusí celú
zachytiť. Port sa môže odpojiť; po opätovnom pripojení použite STATUS na
overenie verzie a PAUZA. RESET je hardvérový reset cez `machine.reset()`,
rovnako ako položka Restart v menu. Nie je to nahratie nového firmvéru.

### Príklady odpovedí

```text
[STATE] mode=PAUZA; serial: START STOP STATUS HELP RESET
[OK] START mode=REC source=SERIAL interval=60s file=/sd/20261107_120000.csv sd=OK
[OK] STOP mode=PAUZA source=SERIAL file=/sd/20261107_120000.csv
[ERR] START vyberte interval 5-300 s v menu PAUZA
[ERR] Neznamy prikaz; pouzite HELP
```

Zdroj `BUTTON` sa vypíše pri spustení/zastavení fyzickým tlačidlom;
tlačidlo aj serial používajú spoločné funkcie. Štart aplikácie stále vypíše
BUILD INFO a inicializáciu periférií; po dokončení inicializácie pribudne
`[STATE] mode=PAUZA`. Počas PAUZA sa nevypisuje periodický heartbeat.
Počas REC zostávajú intervalové výpisy nameraných hodnôt a výsledku SD
zápisu; môžu sa objaviť medzi odpoveďami na príkazy.

STATUS má viacero riadkov s prefixom `[STATUS]` a ukončenie `[STATUS] END`:

- Verzia FW, Git SHA, číslo zostavenia a dirty.
- Režim, aktuálny interval alebo vybraná položka menu, dostupnosť SD,
  počet nájdených DS senzorov a aktuálny/posledný názov CSV (`-` pred prvým REC).
- Aktívna skupina vstupov, RAW, uložený a efektívny počet vzoriek.
- Imp, typická Zadc, PGA, DRATE, nameraná referencia použitá v kóde
  a nominálne napájanie pre výpočet rozsahu.
- Zapnutie deliča, Rgnd, Rin, koeficient K a nominálny rozsah pred deličom.
- Jednotky ADS výstupu, dostupnosť hotovej sady, posledná chyba ADC
  a príznak chyby uloženia nastavení.

Pri ADS Off sa vypíše aj uložená ADS konfigurácia, ale je označená ako
neaktívna; jej rozsah sa netýka pôvodných A1/A2. Pri RAW sa vypíše efektívne
N=1. K a rozsah opisujú nastavený fyzický delič, RAW hodnoty sa nimi nenásobia.
STATUS číta aktuálne hodnoty z RAM, nemení menu, nereskenuje senzory
ani neotvára dátové alebo konfiguračné súbory.

### Vstupný protokol a overenie

Najviac 32 ASCII znakov na riadok. Prázdne riadky sa ignorujú, Backspace
alebo DEL vymaže posledný znak. Príliš dlhý alebo poškodený riadok sa zahodí
celý až po Enter a vráti `[ERR]`; jeho koniec sa nesmie vykonať ako príkaz.
Neznáme príkazy a príkazy s argumentmi vrátia chybu s odkazom na HELP.
Nie je implementované vzdialené nastavenie, Python eval ani prenos súborov.
Limit je jeden príkaz a najviac 64 vstupných znakov za iteráciu hlavnej
slučky (najmenej približne 50 ms plus práca periférií); neposielajte
neobmedzený tok príkazov. Spracovanie nečaká na dokončenie riadka,
čítanie USB ani práca so súbormi nie sú v IRQ.

Balík pripravte ako novú vývojovú verziu bez nového Git tagu:

```bash
python3 tools/prepare_firmware.py --version 1.0.7-dev
```

Pri nasadení po STOP a zálohe preneste **`main.py`**, nový
**`serial_commands.py`** a čerstvý **`build_info.py`** z `work/firmware/`.
Zvyšné moduly musia zodpovedať balíku 1.0.6-dev s deličom; `.cfg` zachovajte.
Archívy 1.0.6-dev v `work/distribution/` sú záloha staršieho stavu a
nové príkazy neobsahujú.

Všetkých **54 PC testov prešlo**. Testy pokrývajú rámcovanie a čiastočné
riadky, CR/LF, pretečenie,
poškodený vstup a nedostupné USB, START/STOP a ich opakovanie, blokovanie
START v menu, STATUS/HELP bez zmeny nastavení, chybu pri tvorbe názvu súboru
a spoločné prechody tlačidla a serialu. RESET je testovaný na odmietnutie
mimo PAUZA, poradie synchronizácie pred resetom a odmietnutie resetu pri
chybe synchronizácie. Pred nasadením zostáva na Pico
overiť USB poll, príkazy počas reálneho merania, odozvu STOP, zachovanie
konfigurácie a skutočný zápis SD. Výsledky nasadenia sú uvedené nižšie.


### Nasadenie sériového ovládania – 7. 11. 2026

Po potvrdení STOP používateľom bol na Pico RP2040 s MicroPythonom 1.27.0
nasadený FW `1.0.7-dev`, Git `32323837`, build `71 dirty`. Záloha siedmich
existujúcich aplikačných súborov a štyroch existujúcich `.cfg` je v
`work/pico-before-serial-20261107/` (nie záloha celej SD karty).
Nahrali sa `main.py`, nový `serial_commands.py` a čerstvý `build_info.py`.
Ostatných päť modulov už zodpovedalo balíku. Overili sa kontrolné súčty
všetkých ôsmich súborov, syntax a inicializácia USB poll na doske.

Zachované nastavenia: ADS On, N=1, RAW Off, Imp Hi, Del No;
uložené Rgnd=10000 Ω, Rin=10000 Ω. Štart potvrdil SELFCAL OK a SD pripravená.
Cez USB sa overili STATUS, HELP, opakovaný STOP v PAUZA, START do REC,
odmietnutie RESET počas REC a STOP späť do PAUZA. Skúšobný REC bol kratší
než interval 60 s a nedosiahol prvý plánovaný zápis. RESET v PAUZA
reštartoval aplikáciu; následný STATUS potvrdil 1.0.7-dev, PAUZA a `file=-`.
Po prvom opätovnom pripojení terminálu prišla jedna odpoveď na neznámy
príkaz; po odoslaní prázdneho riadka a STATUS už bola odpoveď úplná.
Pri pripojení/reštarte počkajte na pripravenosť USB; prípadný neúplný riadok
ukončite Enter a príkaz odošlite znova.

Protokoly `verification-after.txt`, `serial-smoke-test.txt`,
`serial-control-test.txt` a `status-after-reconnect.txt` sú v priečinku
zálohy. Pico zostalo v PAUZA. Dlhý REC, reálny zápis na SD ovládaný
serialom, súčasné fyzické ovládanie, všetky konfigurácie a odozva pri
chybách periférií neboli týmto krátkym overením otestované.
