# Multi-Channel DataLogger (RPi Pico)

Tento projekt predstavuje robustný amatérsky datalogger postavený na mikrokontroléri Raspberry Pi Pico. Zariadenie monitoruje teplotu, vlhkosť, analógové napätia, binárne vstupy a stav batérie.

## 🚀 _**Kľúčové vlastnosti**_
Presné meranie: SHT4x (teplota/vlhkosť) a viacero DS18B20 (OneWire zbernica).
Analógové vstupy: 2x 0-3.3V ADC + monitorovanie napätia vstavanej batérie cez spínaný delič (nulová spotreba v režime spánku).
Binárne vstupy: 4x digitálny vstup pre logické stavy.
Ukladanie dát: SD karta (SPI) s funkciou uos.sync(), ktorá bráni poškodeniu FAT tabuľky pri výpadku napájania.
Používateľské rozhranie: 0.96" OLED displej a rotačný enkodér s obsluhou cez prerušenia (IRQ) pre maximálnu odozvu.
Presný čas: Externý RTC DS3231 synchronizovaný s interným RTC procesora.

## 🛠 _**Hardvérová konfigurácia (Pinout)**_
Komponent	Pin (GP)	Funkcia
I2C0 (SDA/SCL)	8 / 9	OLED, RTC DS3231, SHT4x
SPI0 (SCK/MOSI/MISO)	18/19/16	SD Karta
SD Card CS	17	Chip Select pre SD
OneWire (DS18B20)	22	Teplotné senzory
Rotačný enkodér	12 (CLK), 13 (DT)	Ovládanie menu (IRQ)
Tlačidlo enkodéra	15	Prepínanie režimov (Pauza/REC/Test)
Binárne vstupy	2, 3, 4, 5	Digitálne vstupy (Pull-up)
ADC Vstupy	26, 27	Analógové meranie
Battery Monitor	28 (ADC), 21 (CTRL)	Meranie batérie cez tranzistory
Stavová LED	14	Signalizácia zápisu a chýb

## 📁 _**Štruktúra súborov**_
main.py - Hlavná aplikačná logika a meracia slučka.
lib/ (potrebné knižnice):
sdcard.py
ssd1306.py
ds3231.py
sht4x.py

⚙️ _**Prevádzkové režimy**_
PAUZA (STOP): Zariadenie meria, ale neukladá. Enkodérom je možné nastaviť interval zápisu (v 5s krokoch).
REC (ZÁPIS): Dáta sa ukladajú do CSV súboru s názvom podľa dátumu a času (YYYYMMDD_HHMMSS.csv).
TEST: Špeciálny režim (aktivuje sa pri intervale 0s). Umožňuje listovať zoznamom pripojených OneWire senzorov a zobraziť ich unikátne ID a aktuálnu teplotu.

## 💾 _**Formát dát (CSV)**_
Zariadenie pri každom novom meraní vytvorí hlavičku s ID všetkých pripojených senzorov:
Cas, SHT_T, SHT_H, A1, A2, BIN, B1, B2, B3, B4, [ID_senzorov...]

## 🛡 _**Stabilita a bezpečnosť**_
Prerušenia (IRQ): Enkodér je obsluhovaný mimo hlavnej slučky, čo zaručuje plynulé ovládanie aj počas zápisu na kartu.
Robustný zápis: Po každom riadku sa vykonáva flush() a sync(), čo minimalizuje riziko straty dát.
Garbage Collection: Automatické čistenie RAM pre dlhodobú stabilitu bez zamŕzania.
Poznámka: Pre správnu funkciu merania batérie je potrebné mať osadený delič napätia so spínacím MOSFET tranzistorom na GP21, aby sa zabránilo vybíjaniu batérie počas nečinnosti.

## 🔌 _**Schéma zapojenia (Pinout)**_
             Raspberry Pi Pico (Pinout)
            +---------------------------+
        [ ] | [01] GP0              VBUS| [40] --- +5V USB
        [ ] | [02] GP1              VSYS| [39] --- Napájanie (+5V In)
(BIN 0) [ ] | [03] GP2               GND| [38] --- Spoločná zem
(BIN 1) [ ] | [04] GP3              EN  | [37]
(BIN 2) [ ] | [05] GP4            VREF  | [36]
(BIN 3) [ ] | [06] GP5             GP28 | [35] --- ADC BAT (cez delič)
        [ ] | [07] GND             GP27 | [34] --- ADC 2 (vstup 2)
(I2C SDA)[ ]| [08] GP8             GP26 | [33] --- ADC 1 (vstup 1)
(I2C SCL)[ ]| [09] GP9              RUN | [32]
        [ ] | [10] GND             GP22 | [31] --- OneWire (DS18B20)
        [ ] | [11] GP10            GP21 | [30] --- BAT CTRL (Spínanie deliča)
(ENC CLK)[ ]| [12] GP12            GND  | [29]
(ENC DT) [ ]| [13] GP13            GP20 | [28]
(LED EXT)[ ]| [14] GP14            GP19 | [27] --- SPI MOSI (SD Karta)
(BUTTON) [ ]| [15] GP15            GP18 | [26] --- SPI SCK  (SD Karta)
(SPI MISO)[ ]| [16] GP16            GP17 | [25] --- SPI CS   (SD Karta)
        [ ] | [17] GND             GND  | [24]
            +---------------------------+

Detailné zapojenie modulov
### **1. I2C Zbernica (GP8, GP9) - Napájanie 3.3V**
Všetky zariadenia sú zapojené paralelne na jednu zbernicu:
OLED 0.96" (SSD1306)
RTC DS3231 (Hodiny reálneho času)
SHT4x (Senzor teploty/vlhkosti)
Poznámka: Nezabudni na 4.7kΩ pull-up odpory na SDA a SCL, ak ich moduly už neobsahujú.
### **2. SD Karta (SPI0)**
VCC: 3.3V
GND: Ground
CS: GP17
SCK: GP18
MOSI: GP19
MISO: GP16
### **3. OneWire (GP22)**
DS18B20: Všetky senzory paralelne (Data na GP22, VCC na 3.3V, GND).
Pull-up: Medzi GP22 a 3.3V musí byť odpor 4.7kΩ.
### **4. Monitorovanie batérie (Power Management)**
Pre nulovú spotrebu v nečinnosti je použitý spínaný delič:

 BAT (+) --- [ R1: 10k ] ---+--- [ R2: 10k ] --- [ MOSFET/BSS92 ] --- GND

                            |
                         GP28 (ADC)
                            |
                         GP21 (Ovládanie spínania cez BS170)

### **5. Ovládacie prvky**
Enkodér: CLK (GP12), DT (GP13). Pridané 10nF kondenzátory proti GND na filtráciu zákmitov.
Tlačidlo: GP15 (spína proti GND, interný pull-up aktívny).
LED: GP14 cez 220Ω odpor proti GND.
