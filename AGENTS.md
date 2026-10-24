# MultiChannel datalogger – pokyny pre AI

## Komunikácia a rozsah práce
- Odpovedaj po slovensky, zrozumiteľne a stručne. Používateľ sa učí pracovať so Zedom.
- Rieš jednu konkrétnu úlohu naraz. Načítaj len relevantné súbory; nečítaj celý repozitár, PDF ani namerané dáta bez potreby.
- Pri otázke vysvetľuj; súbory upravuj, keď to zadanie vyžaduje. Zachovaj existujúci štýl a nerob nesúvisiace prepisovanie.
- Pred zmenou prečítaj dotknutý kód a príslušnú dokumentáciu. Pri rozpore medzi nimi ho pomenuj a over skutočné správanie.

## Projekt a súbory
- Cieľová doska: Raspberry Pi Pico, RP2040. Na skúšanej doske bol overený MicroPython 1.27.0; kompatibilitu s inou verziou nepredpokladaj.
- `firmware/main.py`: aplikácia, inicializácia periférií a ovládanie.
- `firmware/ads1256.py`: externý ADC; `adc_average.py`: priemerovanie; `logger_csv.py`: CSV pomocné funkcie.
- Ostatné súbory vo `firmware/` sú ovládače a pomocné skripty. Skripty TimeSet/TimeSyncPC môžu meniť čas; nespúšťaj ich pri bežnej kontrole.
- `firmware/README.md`: prevádzka a postupy overenia; `hardware/schematic/ADS1256_J3.md`: zapojenie ADS1256. Hardvér je v `hardware/`, dokumentácia a vzorky dát v `docs/`.
- Firmware musí fungovať v MicroPythone. Nepridávaj závislosti od CPython-only knižníc. Nespúšťaj `main.py` na PC: vyžaduje modul `machine` a fyzické periférie.

## Zachovanie funkcií a hardvéru
- Zachovaj GPIO podľa aktuálneho kódu a schémy. I2C0: GP8/9; SD SPI0: GP18/19/16, CS GP17; OneWire GP22; enkodér GP12/13 a tlačidlo GP15; LED GP14; batéria GP28/21.
- ADS1256 a pôvodné analógové/binárne vstupy zdieľajú GPIO. Musia sa inicializovať vzájomne výlučne. Softvérové prepnutie nenahrádza správne zapojenie J3.
- Zmeny vstupného režimu a priemerovania povoľuj iba v PAUZA, nie počas REC. Zachovaj reakcie ovládania; nepridávaj dlhé blokovanie hlavnej slučky ani prácu so súbormi v IRQ.
- Priemerovanie používa 1, 2, 4, 8, 16 alebo 32 čerstvých vzoriek na kanál. Nezamieňaj rýchlosť ADC s rýchlosťou hotových osemkanálových výsledkov. Pri zmene konfigurácie nesmie zostať zmiešaná rozpracovaná dávka.
- Zachovaj spracovanie chýb, ukladanie na SD, formát a názvy CSV stĺpcov, pokiaľ zadanie výslovne nežiada zmenu. Nemeň nameranú referenciu ADS1256 bez podkladov.

## Overovanie a doska
- Existujúce testy logiky na PC: `python3 -m unittest discover -s firmware/tests`. Výsledok testov na PC nie je dôkazom funkcie hardvéru.
- Po úprave spusti relevantné testy; pri zmene logiky doplň zmysluplný test. Pri zmene iba dokumentácie testy firmvéru netreba.
- Komunikácia s doskou používa `mpremote` v projektovom `.venv`. Port zisti cez `mpremote connect list`; `/dev/ttyACM0` je iba doteraz použitý port.
- Pred prerušením programu alebo resetom musí byť záznam zastavený v PAUZA. Nahrávanie, mazanie súborov, reset alebo zmenu firmware vykonaj iba pri jasnom zadaní pre konkrétnu dosku. Pred prepísaním urob zálohu dotknutých súborov z dosky.
- Súbory na doske môžu byť odlišné od repozitára. Záloha Python súborov nie je záloha celej SD karty. Nenahrávaj hromadne celý priečinok `firmware/` vrátane testov a dokumentácie.
- Po zmene stručne uveď čo sa zmenilo, čo bolo skutočne overené a čo musí používateľ preveriť na Pico.

## Git a pracovné dáta
- Pred úpravami skontroluj `git status`. Zachovaj používateľove zmeny; nepoužívaj deštruktívny reset ani force push.
- `.venv/` a `work/` obsahujú lokálne prostredie, skúšky a zálohy. Nepridávaj ich do commitov; nepoužívaj slepo `git add .`.
- Commit a push vykonaj iba na používateľovu požiadavku. GitHub origin používa SSH; nevkladaj kľúče, heslá ani tokeny do súborov či výstupov.
- Web použi, keď úloha potrebuje externé overenie; pri čisto lokálnom vysvetlení ho zbytočne nevolaj.

## Správa verzií
- Pred nasadením spusti na PC `python3 tools/prepare_firmware.py`. Generuje balík do `work/firmware/` a `build_info.py` z Git tagu, SHA, počtu commitov a stavu dirty.
- Nasadzuj aktuálny balík a jeho metadáta spolu; nevydávaj starý `build_info.py` za identifikáciu nového kódu. Metadáta nie sú dôkazom zhodnosti všetkých súborov na doske.
- Bez tagu je verzia `0.0.0-dev`. Prvý tag a publikovanie vydania určí používateľ. Nevytváraj ani neposúvaj tagy pri obyčajnej úprave.
- Postup je v `firmware/README.md`; testy verziovania sú v `firmware/tests/test_build_info.py`.
