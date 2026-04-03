import time

class SHT4X:
    def __init__(self, i2c, address=0x44):
        self._i2c = i2c
        self._address = address

    def measurements(self):
        self._i2c.writeto(self._address, b'\xFD')
        time.sleep_ms(10)
        data = self._i2c.readfrom(self._address, 6)
        t_raw = data[0] << 8 | data[1]
        h_raw = data[3] << 8 | data[4]
        temp = -45 + 175 * t_raw / 65535
        humi = -6 + 125 * h_raw / 65535
        return round(temp, 2), round(humi, 2)