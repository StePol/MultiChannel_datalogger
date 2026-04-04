# **Navrhovaná schéma zapojenia**
Pre správne spínanie P-MOSFETu pomocou 3,3V logiky Raspberry Pi Pico (keďže napätie batérie môže byť až 4,2V) je ideálne použiť kombináciu s malým N-MOSFETom. 
Medium
Medium
P-MOSFET (napr. Si2301, BSS84):
Source (S): K plusovému pólu batérie (VBAT).
Drain (D): K hornému rezistoru napäťového deliča (
).
Gate (G): K Drainu N-MOSFETu a cez pull-up rezistor (

) k batérii.
N-MOSFET (napr. 2N7002, BSS138):
Source (S): Na zem (GND).
Gate (G): K GPIO pinu Pico (napr. GP15).
Drain (D): K Gate P-MOSFETu.
Napäťový delič:
Zapojte 
 a 
 (napr. oba 

) medzi Drain P-MOSFETu a GND.
Stred deliča pripojte k ADC pinu Pico (napr. ADC0/GP26). 
Medium
Medium
 +3
Princíp fungovania
Vypnutý stav: GPIO pin je LOW. N-MOSFET je vypnutý, pull-up rezistor drží Gate P-MOSFETu na napätí batérie (

), takže P-MOSFET je zatvorený a cez delič netečie žiadny prúd.
Meranie: Nastavte GPIO na HIGH. N-MOSFET sa otvorí a stiahne Gate P-MOSFETu k zemi. P-MOSFET sa otvorí, delič sa pripojí k batérii a ADC môže odčítať hodnotu. 
Medium
Medium
 +1
Príklad kódu (MicroPython)
python
from machine import Pin, ADC
import time

# Konfigurácia pinov
ctrl_pin = Pin(15, Pin.OUT)  # Ovládanie MOSFETov
adc = ADC(Pin(26))           # Meranie napätia

def get_battery_voltage():
    ctrl_pin.value(1)        # Zapnúť delič
    time.sleep_ms(10)        # Stabilizácia napätia
    
    # Prepočet: ADC(0-65535) -> 0-3.3V, delič 1:1 -> 0-6.6V
    raw = adc.read_u16()
    voltage = (raw / 65535) * 3.3 * 2
    
    ctrl_pin.value(0)        # Vypnúť delič (odstránenie parazitného odberu)
    return voltage

print(f"Napätie batérie: {get_battery_voltage():.2f} V")
Kód používajte opatrne.

Upozornenie: Pri použití deliča 



 je výstupné napätie pri plnej batérii (


) rovné 


, čo je bezpečne pod limitom 


 pre ADC pin. 
Adafruit Forums
Adafruit Forums
