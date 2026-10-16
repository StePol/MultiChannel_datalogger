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

## Manual input-mode switch

Set the constant at the start of `main.py`, then restart the Pico:

```python
ADS1256_ENABLED = True   # ADS1256 AN0–AN7 instead of A1/A2 and B1–B4
# ADS1256_ENABLED = False  # original two analog and four digital inputs
ADS1256_VREF = 2.503     # measured reference voltage of the tested module
```

The default is ADS1256 enabled. This is a source-code setting, not an
encoder menu item. Copy `ads1256.py` and `logger_csv.py` along with `main.py`
and the existing drivers to the Pico.

The input configurations are mutually exclusive: GP2–GP5 and GP26/GP27
are initialized only for the selected mode. Connect J3 for that mode before
power-up; disconnect the ADS1256 module when using the original inputs.
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

A complete scan is started one second after the previous scan finishes;
the ADC's 100 SPS setting is not the rate of complete eight-channel scans.
The OLED rotates through channel pairs every two seconds. CSV stores the
latest complete scan with six decimal places in volts. On a read failure,
all eight values are invalidated, the OLED shows `ADS1256 CHYBA`, and CSV
contains eight empty cells. Subsequent scans retry. Startup initialization
failure requires checking the module and restarting the Pico; the firmware
does not fall back to the conflicting original GPIO assignments.

## Verification in Thonny

1. Select **Run → Select interpreter → MicroPython (Raspberry Pi Pico)**.
2. Stop the running application with **Stop/Restart backend**.
3. Upload `ads1256.py`, `logger_csv.py` and the updated `main.py` to the
   root of **Raspberry Pi Pico** in Thonny's Files pane. Keep the existing
   peripheral drivers on the Pico.
4. Set `ADS1256_ENABLED = True` and `ADS1256_VREF = 2.503` in the Pico's
   `main.py`, save it there and restart the board.
5. In Shell, check the startup message confirming AN0–AN7 and SELFCAL OK.
   Confirm that the OLED rotates through all eight input values.
6. Select a 5-second recording interval. Check the Shell values and the
   new CSV file: columns AN0–AN7 must be present and the old A1/A2/BIN
   columns absent. Check that battery and temperature readings remain.
7. To test the original mode, stop and power off the Pico, disconnect the
   ADS1256 and restore the original J3 inputs. Set the switch to `False`,
   save and restart. Check that the original CSV columns return.

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
- **TEST** — displays connected DS18B20 sensors, their ROM IDs and temperatures.
- **SYNC** — synchronizes the external DS3231 RTC with the current internal RTC time.

While in PAUZA mode, the rotary encoder selects `SyncRTC`, `TEST`, or a
logging interval from 5 to 300 seconds in 5-second steps.

## CSV Format

Each recording creates a new timestamped CSV file.

With `ADS1256_ENABLED = False`, the fixed columns are:

```text
Cas,SHT_T,SHT_H,A1,A2,BAT,BIN,B1,B2,B3,B4
```

With `ADS1256_ENABLED = True`, they are:

```text
Cas,SHT_T,SHT_H,AN0,AN1,AN2,AN3,AN4,AN5,AN6,AN7,BAT
```

The ROM ID of each detected DS18B20 sensor is appended to the header as an
additional column.

An example recording is available in `../docs/data/`.

## Firmware Files

| File | Description |
|---|---|
| `main.py` | Main application, manual input switch and measurement loop |
| `ads1256.py` | J3 ADS1256 driver, eight single-ended inputs |
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
Deployment and verification of this integrated version on Pico are pending.
