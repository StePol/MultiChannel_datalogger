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
**SyncRTC** and **TEST**, then press the encoder button to open its submenu.
Turn toward **On** or **Off** and press again to confirm and return to PAUZA:

- **On** initializes and calibrates ADS1256 and selects AN0–AN7.
- **Off** selects the original A1/A2 and B1–B4 inputs.

Rotation only changes the highlighted choice; confirmation applies it.
The menu cannot be entered during REC. Stop recording first. Switching
happens immediately without restarting. A new recording uses the CSV layout
for the selected input mode. The selection is kept in RAM; after restarting,
`ADS1256_ENABLED = True` in `main.py` supplies the default (On).
`ADS1256_VREF = 2.503` remains the measured reference setting.

Copy `ads1256.py`, `adc_average.py` and `logger_csv.py` along with `main.py` and the existing
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

The OLED rotates through channel pairs every two seconds. Both display
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
   initialization and confirm that the OLED rotates through channel pairs.
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
- **TEST** — displays connected DS18B20 sensors, their ROM IDs and temperatures.
- **SYNC** — synchronizes the external DS3231 RTC with the current internal RTC time.

While in PAUZA mode, the rotary encoder selects `ADS1256`, `SyncRTC`,
`TEST`, or a logging interval from 5 to 300 seconds in 5-second steps.

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
