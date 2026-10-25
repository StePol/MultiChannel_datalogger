# Firmware

This directory contains the software running on the Raspberry Pi Pico (RP2040).

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
The averaging count remains a RAM-only setting, defaulting to 1 at startup.
`ADS1256_VREF = 2.503` remains the measured reference setting.

Copy `input_settings.py`, `ads1256.py`, `adc_average.py` and `logger_csv.py` along with `main.py` and the existing
drivers to the Pico. Thonny is the development and upload environment.

The input configurations are mutually exclusive: GP2–GP5 and GP26/GP27
are initialized only for the selected mode. The software selection does not change external wiring or remove module
power. Use the original inputs only with the corresponding J3 wiring;
disconnect the ADS1256 before connecting original input signals.
Battery measurement on GP28/GP21, SHT4x, DS18B20, RTC and SD logging remain
available in both modes.

ADS1256 uses manual SPI with the tested 2 µs bit timing, buffer off, PGA=1,
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

The default is 1 (no averaging). The selected count is kept in RAM and
returns to 1 after restart. For each output set, the logger takes N fresh
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
and CSV use the latest completed average, with six decimal places in volts.
If the logging interval is shorter than the averaging cycle, consecutive
CSV rows can contain the same completed average. Before the first batch
finishes, channel cells are empty and the display shows `ADS meranie...`.
CSV column names and layout are unchanged. The chosen sample count is
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

With ADS1256 **On**, they are:

```text
Cas,SHT_T,SHT_H,AN0,AN1,AN2,AN3,AN4,AN5,AN6,AN7,BAT
```

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
