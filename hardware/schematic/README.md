# MultiChannel Datalogger – Hardware

This directory contains the KiCad hardware design files for the
MultiChannel Datalogger.

## KiCad version

The project is maintained with **KiCad 10**.

Open the project using:

`MultiChannel_datalogger.kicad_pro`

Do not open only the `.kicad_sch` file when working on the complete project.

## Project files

| File / Directory | Description |
|---|---|
| `MultiChannel_datalogger.kicad_pro` | KiCad project file |
| `MultiChannel_datalogger.kicad_sch` | Electrical schematic |
| `MultiChannel_datalogger.kicad_pcb` | PCB design |
| `MultiChannel_datalogger.pdf` | PDF export of the schematic |
| `MultiChannel_datalogger.csv` | Component/BOM export |
| `ADS1256_J3.md` | Tested ADS1256 24-bit ADC connection via J3 |
| `sym-lib-table` | Project symbol library configuration |
| `fp-lib-table` | Project footprint library configuration |
| `libraries/` | Project-specific symbols and footprints |

## Project libraries

Project-specific KiCad libraries are stored locally in the `libraries/`
directory so that the project does not depend on absolute paths on the
developer's computer.

The library tables use `${KIPRJMOD}` relative paths.

Currently included:

- Raspberry Pi / RP2040 symbol library
- Raspberry Pi Pico footprint
- RP2040 QFN-56 footprint
- HC49-US crystal footprint

## Portability

The repository is intended to contain all project-specific KiCad files
required to open the hardware design on another computer after cloning
the repository.

Standard symbols and footprints supplied with KiCad may still use the
standard KiCad libraries.

KiCad user-specific files, lock files, history and automatic backups are
excluded from Git.

## PCB status

The PCB project file is included, but the PCB layout has not yet been
designed.

## Generated files

`MultiChannel_datalogger.pdf` and `MultiChannel_datalogger.csv` are
generated from the schematic and should be updated when the schematic
changes significantly.
