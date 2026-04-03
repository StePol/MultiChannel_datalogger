import machine
import ds3231
import time

# Inicializácia I2C pre RTC
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9))
rtc_ext = ds3231.DS3231(i2c)

def sync_rtc_from_pc():
    # Thonny pri spustení nastaví interné hodiny Pico podľa PC
    t = time.localtime()
    
    # Formát pre rtc.datetime: (rok, mesiac, deň, hodina, minúta, sekunda, deň_v_týždni)
    # t[6] je deň v týždni (0-6)
    rtc_ext.datetime((t[0], t[1], t[2], t[3], t[4], t[5], t[6]))
    
    print("------------------------------------------")
    print("RTC modul bol zosynchronizovaný s PC!")
    print("Aktuálny čas: {:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5]))
    print("------------------------------------------")

sync_rtc_from_pc()
