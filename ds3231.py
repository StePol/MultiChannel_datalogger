from machine import I2C

class DS3231:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = 0x68

    def bcd_to_dec(self, bcd):
        return (bcd // 16) * 10 + (bcd % 16)

    def dec_to_bcd(self, dec):
        return (dec // 10) * 16 + (dec % 10)

    def datetime(self, dt=None):
        if dt is None:
            data = self.i2c.readfrom_mem(self.addr, 0, 7)
            return (
                self.bcd_to_dec(data[6]) + 2000, self.bcd_to_dec(data[5] & 0x7f),
                self.bcd_to_dec(data[4]), self.bcd_to_dec(data[2]),
                self.bcd_to_dec(data[1]), self.bcd_to_dec(data[0]),
                self.bcd_to_dec(data[3]) - 1
            )
        res = bytearray(7)
        res[0], res[1], res[2] = self.dec_to_bcd(dt[5]), self.dec_to_bcd(dt[4]), self.dec_to_bcd(dt[3])
        res[3] = self.dec_to_bcd(dt[6] + 1)
        res[4], res[5], res[6] = self.dec_to_bcd(dt[2]), self.dec_to_bcd(dt[1]), self.dec_to_bcd(dt[0] - 2000)
        self.i2c.writeto_mem(self.addr, 0, res)

    def get_time(self):
        return self.datetime()