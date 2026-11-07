"""Persistent ADS1256 mode and averaging count in the Pico filesystem."""
import os

SAMPLE_OPTIONS = (1, 2, 4, 8, 16, 32)


def _read_value(path):
    try:
        with open(path, "r") as source:
            return source.read(64).strip()
    except OSError:
        return None


def _read_mode(path):
    value = _read_value(path)
    if value == "On":
        return True
    if value == "Off":
        return False
    return None


def load_input_mode(path="input_mode.cfg"):
    # Missing or invalid settings select the original inputs.
    return _read_mode(path) is True


def save_input_mode(enabled, path="input_mode.cfg"):
    enabled = bool(enabled)
    if _read_mode(path) is enabled:
        return False
    _write_value("On" if enabled else "Off", path)
    return True


def load_sample_count(path="ads_samples.cfg"):
    value = _read_value(path)
    for count in SAMPLE_OPTIONS:
        if value == str(count):
            return count
    return 1


def save_sample_count(count, path="ads_samples.cfg"):
    if type(count) is not int or count not in SAMPLE_OPTIONS:
        raise ValueError("Unsupported ADS1256 sample count")
    value = str(count)
    if _read_value(path) == value:
        return False
    _write_value(value, path)
    return True


def _write_value(value, path):
    # Keep the previous setting until the complete new file is synced.
    temporary = path + ".tmp"
    with open(temporary, "w") as target:
        target.write(value + "\n")
    os.sync()
    os.rename(temporary, path)
    os.sync()


def load_raw_mode(path="ads_raw.cfg"):
    return load_input_mode(path)


def save_raw_mode(enabled, path="ads_raw.cfg"):
    return save_input_mode(enabled, path)


def load_buffer_mode(path="ads_buffer.cfg"):
    return load_input_mode(path)


def save_buffer_mode(enabled, path="ads_buffer.cfg"):
    return save_input_mode(enabled, path)



def load_divider(path="ads_divider.cfg"):
    from adc_divider import DEFAULT_DIVIDER, validate_divider
    value = _read_value(path)
    try:
        mode, rgnd, rin = value.split(",")
        if mode not in ("On", "Off"):
            return DEFAULT_DIVIDER
        return validate_divider((mode == "On", int(rgnd), int(rin)))
    except (AttributeError, ValueError, TypeError):
        return DEFAULT_DIVIDER


def save_divider(config, path="ads_divider.cfg"):
    from adc_divider import validate_divider
    enabled, rgnd, rin = validate_divider(config)
    value = "{},{},{}".format("On" if enabled else "Off", rgnd, rin)
    if _read_value(path) == value:
        return False
    _write_value(value, path)
    return True
