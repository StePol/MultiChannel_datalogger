"""Shared input divider for ADS1256, PGA=1, 100 SPS, CLKIN=7.68 MHz.

Uin -- Rin -- AINx -- Rgnd -- GND; AINCOM is tied to GND.
The ADC's typical effective impedance loads Rgnd in parallel.
"""

MAX_RESISTANCE = 99999999
DEFAULT_DIVIDER = (False, 10000, 90000)  # enabled, Rgnd, Rin [ohm]


def validate_divider(config):
    enabled, rgnd, rin = config
    if type(enabled) is not bool:
        raise ValueError("divider enabled must be bool")
    if (type(rgnd) is not int or type(rin) is not int or
            not 1 <= rgnd <= MAX_RESISTANCE or not 0 <= rin <= MAX_RESISTANCE):
        raise ValueError("invalid divider resistance")
    return enabled, rgnd, rin


def input_impedance(buffer_enabled):
    # TI ADS1256 table 3: 40 Mohm at 100 SPS, not 80 Mohm (<=50 SPS).
    return 40000000.0 if buffer_enabled else 150000.0


def divider_factor(config, buffer_enabled):
    enabled, rgnd, rin = validate_divider(config)
    if not enabled:
        return 1.0
    # 1 + Rin / (Rgnd || Zadc), avoiding a large resistor product.
    return 1.0 + rin / rgnd + rin / input_impedance(buffer_enabled)


def measurement_range(config, buffer_enabled, avdd=5.0, vref=2.503):
    # Nominal positive range for AINCOM=GND, not a measured supply voltage.
    pin_limit = min(avdd - 2.0 if buffer_enabled else avdd, 2.0 * vref)
    return max(0.0, pin_limit) * divider_factor(config, buffer_enabled)


def scale_values(values, raw, config, buffer_enabled):
    if values is None or raw or not config[0]:
        return values
    factor = divider_factor(config, buffer_enabled)
    return [value * factor for value in values]


def divider_label(config, buffer_enabled):
    return ("Del:1:{:.5g}".format(divider_factor(config, buffer_enabled))
            if config[0] else "Del:No")


def voltage_label(channel, value):
    label = "AN{}: {:.6f}V".format(channel, value)
    if len(label) > 16:
        label = "AN{}: {:.5g}V".format(channel, value)
    return label


class DividerMenu:
    """Draft changes only; main loop applies/saves, IRQ only calls turn()."""
    def __init__(self, config):
        self.config = validate_divider(config)
        self.rgnd, self.rin = config[1:]
        self.choice = 0
        self.stage = "menu"
        self.digit = 0
        self.value = 0
        self.error = False

    def turn(self, direction):
        if self.stage == "menu":
            self.choice = max(0, min(5, self.choice + direction))
        elif self.stage == "edit":
            place = 10 ** (7 - self.digit)
            old = (self.value // place) % 10
            self.value += (((old + direction) % 10) - old) * place

    def press(self):
        if self.stage == "info":
            self.stage = "menu"
        elif self.stage == "edit":
            if self.digit < 7:
                self.digit += 1
            elif self.choice == 1 and self.value == 0:
                self.error = True
            else:
                if self.choice == 1:
                    self.rgnd = self.value
                else:
                    self.rin = self.value
                self.stage = "menu"
                self.error = False
        elif self.choice in (0, 4):
            self.config = validate_divider((self.choice == 4, self.rgnd, self.rin))
            return "apply"
        elif self.choice == 5:
            return "cancel"
        elif self.choice == 3:
            self.stage = "info"
        else:
            self.stage = "edit"
            self.value = self.rgnd if self.choice == 1 else self.rin
            self.digit = 0
            self.error = False
        return None

    def draw(self, oled, buffer_enabled, avdd=5.0, vref=2.503):
        if self.stage == "edit":
            oled.text("Rgnd [Ohm]" if self.choice == 1 else "Rin [Ohm]", 0, 0)
            oled.text("{:08d}".format(self.value), 0, 18)
            oled.hline(self.digit * 8, 28, 8, 1)
            oled.text("Rgnd musi byt >0" if self.error else "Otoc = cislica", 0, 40)
            oled.text("Klik = dalsia", 0, 54)
        elif self.stage == "info":
            # Preview the entered resistors as an enabled divider.
            config = (True, self.rgnd, self.rin)
            oled.text("Navrh [Ohm]", 0, 0)
            oled.text("Rgnd:{}".format(self.rgnd), 0, 10)
            oled.text("Rin:{}".format(self.rin), 0, 20)
            oled.text("K:{:.6g}".format(divider_factor(config, buffer_enabled)), 0, 30)
            oled.text("0-{:.6g} V".format(measurement_range(config, buffer_enabled, avdd, vref)), 0, 40)
            oled.text("Akt:0-{:.4g}V".format(measurement_range(
                self.config, buffer_enabled, avdd, vref)), 0, 54)
        else:
            oled.text("Delic [Ohm]", 0, 0)
            labels = ("No", "Rgnd:{}".format(self.rgnd), "Rin:{}".format(self.rin),
                      "Prevod/rozsah", "Pouzit", "Spat")
            first = max(0, self.choice - 3)
            for row, index in enumerate(range(first, min(first + 4, len(labels)))):
                oled.text(("> " if index == self.choice else "  ") + labels[index],
                          0, 14 + row * 12)
