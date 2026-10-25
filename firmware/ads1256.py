"""ADS1256 on J3, manual SPI matching the tested 2 us diagnostic timing.

TI SBAS288K: https://www.ti.com/lit/ds/symlink/ads1256.pdf
Single-ended AIN0..AIN7 against AINCOM; buffer off, PGA=1, 100 SPS.
"""
from machine import Pin
import time


class ADS1256:
    def __init__(self, vref=2.503, timeout_ms=1000):
        if vref <= 0:
            raise ValueError("VREF must be positive")
        self.vref = vref
        self.timeout_ms = timeout_ms
        self.cs = Pin(5, Pin.OUT, value=1)
        self.sclk = Pin(2, Pin.OUT, value=0)
        self.din = Pin(3, Pin.OUT, value=0)
        self.dout = Pin(4, Pin.IN)
        self.drdy = Pin(26, Pin.IN)
        self.rst = Pin(27, Pin.OUT, value=1)
        self.rst.value(0)
        time.sleep_ms(10)
        self.rst.value(1)
        time.sleep_ms(100)
        self._wait_ready()
        self._command(0x0F)  # SDATAC: explicit RDATA mode
        if self._read_reg(0) >> 4 != 3:
            raise OSError("ADS1256 CHIP ID != 3")
        # STATUS: MSB first, buffer off, auto-calibration off.
        for reg, value in ((0, 0x00), (1, 0x08), (2, 0x20), (3, 0x82)):
            self._write_reg(reg, value)
            # STATUS: kontrolujeme len ORDER/ACAL/BUFEN, nie živý bit DRDY.
            mask = 0x0E if reg == 0 else 0xFF
            actual = self._read_reg(reg)
            if actual & mask != value:
                raise OSError("ADS1256 register verification failed: reg=0x{:02X} read=0x{:02X} expected=0x{:02X} mask=0x{:02X}".format(
                    reg, actual, value, mask))
        self._command(0xF0)  # SELFCAL after setting PGA and data rate
        time.sleep_ms(1)  # allow DRDY to rise before waiting for completion
        self._wait_ready()

    def _wait_ready(self):
        start = time.ticks_ms()
        while self.drdy.value():
            if time.ticks_diff(time.ticks_ms(), start) >= self.timeout_ms:
                raise OSError("ADS1256 DRDY timeout")
            time.sleep_us(50)

    def _write_byte(self, value):
        for bit in range(7, -1, -1):
            self.sclk.value(0)
            self.din.value((value >> bit) & 1)
            time.sleep_us(2)
            self.sclk.value(1)
            time.sleep_us(2)
            self.sclk.value(0)
            time.sleep_us(2)

    def _read_byte(self):
        value = 0
        self.din.value(0)
        for _ in range(8):
            self.sclk.value(0)
            time.sleep_us(2)
            self.sclk.value(1)
            time.sleep_us(2)
            value = (value << 1) | self.dout.value()
            self.sclk.value(0)
            time.sleep_us(2)
        return value

    def _command(self, command):
        self.cs.value(0)
        try:
            self._write_byte(command)
        finally:
            self.cs.value(1)
        time.sleep_us(10)

    def _write_reg(self, reg, value):
        self.cs.value(0)
        try:
            self._write_byte(0x50 | reg)
            self._write_byte(0)
            self._write_byte(value)
        finally:
            self.cs.value(1)
        time.sleep_us(20)

    def _read_reg(self, reg):
        self.cs.value(0)
        try:
            self._write_byte(0x10 | reg)
            self._write_byte(0)
            time.sleep_us(20)
            return self._read_byte()
        finally:
            self.cs.value(1)
            time.sleep_us(10)

    def read_channel(self, channel):
        if not 0 <= channel <= 7:
            raise ValueError("channel must be 0..7")
        self._wait_ready()
        self._write_reg(1, (channel << 4) | 8)  # negative input = AINCOM
        self._command(0xFC)  # SYNC; 10 us > required 24 CLKIN periods
        self._command(0x00)  # WAKEUP
        self._wait_ready()  # wait for the newly selected channel to settle
        self.cs.value(0)
        try:
            self._write_byte(0x01)  # RDATA
            time.sleep_us(20)
            raw = (self._read_byte() << 16) | (self._read_byte() << 8) | self._read_byte()
        finally:
            self.cs.value(1)
        if raw & 0x800000:
            raw -= 0x1000000
        return raw * (2 * self.vref / 0x7FFFFF)

    def read_all(self):
        return [self.read_channel(channel) for channel in range(8)]
