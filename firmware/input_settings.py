"""Persistent ADS1256 mode and averaging count in the Pico filesystem."""
import os

SAMPLE_OPTIONS = (1, 2, 4, 8, 16, 32)


def _read_value(path):
    try:
        with open(path, "r") as source:
            return source.read(16).strip()
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
