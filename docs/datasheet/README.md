# Datasheets

This directory contains component datasheets and technical notes used during
development of the Multi-Channel DataLogger.

## Sensors and RTC

| File | Component |
|---|---|
| `DS18B20.PDF` | DS18B20 digital temperature sensor |
| `DS3231.PDF` | DS3231 real-time clock |
| `SHT4X.PDF` | SHT4x temperature and humidity sensor |

## Battery Measurement

| File | Description |
|---|---|
| `MeranieNapatiaLiIonBaterie.md` | Project notes for Li-ion battery voltage measurement |
| `2N7000_BS170.PDF` | Vishay Siliconix datasheet covering the BS170 N-channel MOSFET used as Q2 |

The battery measurement circuit is still under development. Files in this
section are retained as design references and should not be interpreted as the
final component selection.

The current electrical design is documented in the KiCad project under
[`../../hardware/schematic/`](../../hardware/schematic/).
