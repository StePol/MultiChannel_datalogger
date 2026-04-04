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
- Temperature
- Humidity
- Voltage / Current
- Additional channels: TBD

## Data Output
- Format: TBD (CSV / UART / I2C display...)
- Logging interval: TBD
