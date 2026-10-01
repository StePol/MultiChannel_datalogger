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

## Measured Parameters
- SHT4x temperature and relative humidity
- Multiple DS18B20 temperature sensors
- Two analog voltage inputs
- Battery voltage
- Four digital inputs

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

The fixed columns are:

```text
Cas,SHT_T,SHT_H,A1,A2,BAT,BIN,B1,B2,B3,B4
```

The ROM ID of each detected DS18B20 sensor is appended to the header as an
additional column.

An example recording is available in `../docs/data/`.

## Firmware Files

| File | Description |
|---|---|
| `main.py` | Main application and measurement loop |
| `ds3231.py` | DS3231 RTC driver |
| `sdcard.py` | microSD card driver |
| `sht4x.py` | SHT4x temperature/humidity driver |
| `ssd1306.py` | SSD1306 OLED driver |
| `TimeSet.py` | RTC utility |
| `TimeSyncPC.py` | RTC synchronization utility |

## Development Status

The battery measurement circuit and the corresponding firmware are still
under development and may change.
