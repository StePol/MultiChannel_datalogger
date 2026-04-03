import machine
import ds3231
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9))
rtc = ds3231.DS3231(i2c)

# NASTAVENIE: (rok, mesiac, deň, hodina, minúta, sekunda)
# Nastavte aktuálny čas a hneď spustite (F5)
rtc.datetime((2026, 2, 15, 12, 30, 0, 0)) 
print("Čas v RTC bol úspešne nastavený!")