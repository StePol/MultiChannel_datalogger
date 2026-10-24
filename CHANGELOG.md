# Zmeny vydaní

## Nevydané

- Štartovacie logo na OLED približne na 2 sekundy, s dynamickou verziou
  z `BUILD_VERSION`. Bitmapa sa pri vydaní novej verzie nemení.
- PC testy vykreslenia a časovania (celkovo 10 testov prešlo).
- Používateľ 24. 10. 2026 na Pico potvrdil logo s dynamickou verziou,
  približne dvojsekundové zobrazenie a návrat na bežnú obrazovku.

## v1.0.0 – 24. 10. 2026

Prvé označené vydanie existujúceho MicroPython dataloggera.

### Pridané

- Príprava balíka na PC cez `tools/prepare_firmware.py`: verzia z najbližšieho
  dosiahnuteľného sémantického Git tagu, krátke SHA, počet commitov a dirty.
- Generovaný `build_info.py` a výpis identifikácie pri štarte aplikácie.
- Náhradné vývojové hodnoty pri chýbajúcom `build_info.py`.
- Testy verziovania, projektové pokyny pre AI a dokumentácia práce zo Zedu.
- Ignorovanie lokálneho prostredia `.venv/`, balíkov a záloh vo `work/`.

### Overenie

- PC: testy priemerovania a verziovania (7 testov).
- Zed: používateľ potvrdil úspešné spustenie úlohy prípravy balíka.
- Pico RP2040 / MicroPython 1.27.0: používateľ potvrdil štartovací výpis
  vývojového balíka, inicializáciu ADS1256 a SD karty, displej a ovládanie.
- Tieto skúšky nepotvrdzujú novú kalibráciu ADC, všetky CSV výstupy ani
  všetky kombinácie režimov priemerovania. Predchádzajúce obmedzenia
  popísané vo firmware/README.md zostávajú platné.

### Nasadenie

Vývojový balík na Pico pri skúške hlásil `0.0.0-dev`, commit `dbf0b39d`,
zostavenie `66 dirty`. Pre identifikáciu vydania `1.0.0` treba po vytvorení
tagu opäť pripraviť balík a preniesť čerstvé metadáta so zodpovedajúcou
aplikáciou. Generované súbory sa neukladajú do Gitu.
