"""CSV layout for the two mutually exclusive input configurations."""


def make_record(clock, temperature, humidity, battery, rom_ids, ds_values,
                ads_enabled, ads_values=None, analog=None, binary=None):
    header = ["Cas", "SHT_T", "SHT_H"]
    row = [clock, "{:.2f}".format(temperature), "{:.1f}".format(humidity)]
    if ads_enabled:
        header += ["AN{}".format(i) for i in range(8)] + ["BAT"]
        # A failed scan produces empty cells, never previous or fabricated values.
        row += (["{:.6f}".format(v) for v in ads_values]
                if ads_values is not None else [""] * 8)
        row += ["{:.2f}".format(battery)]
    else:
        header += ["A1", "A2", "BAT", "BIN", "B1", "B2", "B3", "B4"]
        row += ["{:.2f}".format(analog[0]), "{:.2f}".format(analog[1]),
                "{:.2f}".format(battery), binary] + list(binary)
    header += rom_ids
    row += [str(v) for v in ds_values]
    return ",".join(header) + "\n", ",".join(row) + "\n"
