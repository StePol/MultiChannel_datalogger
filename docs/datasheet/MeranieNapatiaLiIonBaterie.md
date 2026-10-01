# Meranie napätia Li-ion batérie

> **Stav:** Rozpracované. Zapojenie aj firmware pre meranie batérie sa môžu
> ešte zmeniť.

Aktuálny návrh používa spínaný napäťový delič, aby nebol delič trvalo
pripojený k batérii.

## Aktuálne komponenty

Podľa aktuálnej KiCad schémy sú použité:

- **Q1 — BSS84** — P-MOSFET
- **Q2 — BS170** — N-MOSFET
- **R3 — 10 kΩ** — spodný rezistor napäťového deliča
- **R4 — 10 kΩ** — horný rezistor napäťového deliča
- **R5 — 1 kΩ** — sériový rezistor gate Q2
- **R6 — 10 kΩ** — pull-down gate Q2
- **R7 — 10 kΩ** — pull-up gate Q1
- **GP21** — riadenie meracieho obvodu
- **GP28 / ADC2** — meranie napätia batérie

## Princíp zapojenia

P-MOSFET BSS84 pripája napäťový delič k batérii iba počas merania.
Jeho gate je ovládaný pomocou N-MOSFETu BS170.

### Vypnutý stav

GP21 je v stave LOW. BS170 je vypnutý a gate BSS84 je držaný na úrovni
napätia batérie. BSS84 je zatvorený a napäťový delič nie je aktívny.

### Meranie

GP21 sa nastaví na HIGH. BS170 sa otvorí a stiahne gate BSS84 smerom
k GND. BSS84 sa otvorí a pripojí napäťový delič k batérii.

Napätie zo stredu deliča sa následne meria pomocou ADC na GP28.
R4 a R3 majú hodnotu 10 kΩ a vytvárajú napäťový delič s pomerom 1:1.
Napätie na ADC je preto približne polovica napätia batérie. Pri napätí
batérie 4,2 V je na ADC približne 2,1 V.

## Aktuálna implementácia vo firmware

Aktuálny firmware používa tento princíp:

```python
Batt_ctrl_pin.value(1)
v_bat = round((adc_bat.read_u16() * 3.3) / 65535, 2) * 2
Batt_ctrl_pin.value(0)
```

Výpočet momentálne predpokladá napäťový delič s pomerom 1:1.

## Ďalší vývoj

Pred finálnou verziou je potrebné overiť najmä:

- hodnoty rezistorov napäťového deliča
- presnosť merania ADC
- stabilizačný čas po zapnutí meracieho obvodu
- skutočný odber vo vypnutom stave
- kalibráciu meraného napätia
- správanie obvodu v celom rozsahu napätia Li-ion článku

Autoritatívnym zdrojom aktuálneho elektrického zapojenia je KiCad schéma v
[`../../hardware/schematic/`](../../hardware/schematic/).
