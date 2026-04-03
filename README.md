Multi-Channel DataLogger (RPi Pico)
Tento projekt predstavuje robustný priemyselný datalogger postavený na mikrokontroléri Raspberry Pi Pico. Zariadenie monitoruje teplotu, vlhkosť, analógové napätia, binárne vstupy a stav batérie, pričom dáta ukladá na SD kartu s vysokým dôrazom na integritu súborového systému.
🚀 Kľúčové vlastnosti
Presné meranie: SHT4x (teplota/vlhkosť) a viacero DS18B20 (OneWire zbernica).
Analógové vstupy: 2x 0-3.3V ADC + monitorovanie napätia batérie cez spínaný delič (nulová spotreba v režime spánku).
Binárne vstupy: 4x digitálny vstup pre logické stavy.
Ukladanie dát: SD karta (SPI) s funkciou uos.sync(), ktorá bráni poškodeniu FAT tabuľky pri výpadku napájania.
Používateľské rozhranie: 0.96" OLED displej a rotačný enkodér s obsluhou cez prerušenia (IRQ) pre maximálnu odozvu.
Presný čas: Externý RTC DS3231 synchronizovaný s interným RTC procesora.
🛠 Hardvérová konfigurácia (Pinout)
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
📁 Štruktúra súborov
main.py - Hlavná aplikačná logika a meracia slučka.
lib/ (potrebné knižnice):
sdcard.py
ssd1306.py
ds3231.py
sht4x.py
⚙️ Prevádzkové režimy
PAUZA (STOP): Zariadenie meria, ale neukladá. Enkodérom je možné nastaviť interval zápisu (v 5s krokoch).
REC (ZÁPIS): Dáta sa ukladajú do CSV súboru s názvom podľa dátumu a času (YYYYMMDD_HHMMSS.csv).
TEST: Špeciálny režim (aktivuje sa pri intervale 0s). Umožňuje listovať zoznamom pripojených OneWire senzorov a zobraziť ich unikátne ID a aktuálnu teplotu.
💾 Formát dát (CSV)
Zariadenie pri každom novom meraní vytvorí hlavičku s ID všetkých pripojených senzorov:
Cas, SHT_T, SHT_H, A1, A2, BIN, B1, B2, B3, B4, [ID_senzorov...]
🛡 Stabilita a bezpečnosť
Prerušenia (IRQ): Enkodér je obsluhovaný mimo hlavnej slučky, čo zaručuje plynulé ovládanie aj počas zápisu na kartu.
Robustný zápis: Po každom riadku sa vykonáva flush() a sync(), čo minimalizuje riziko straty dát.
Garbage Collection: Automatické čistenie RAM pre dlhodobú stabilitu bez zamŕzania.
Poznámka: Pre správnu funkciu merania batérie je potrebné mať osadený delič napätia so spínacím MOSFET tranzistorom na GP21, aby sa zabránilo vybíjaniu batérie počas nečinnosti.
