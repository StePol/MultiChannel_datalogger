"""Persistent ADS1256 input-mode selection in the Pico internal filesystem."""
import os


def _read_mode(path):
    try:
        with open(path, "r") as source:
            value = source.read(16).strip()
    except OSError:
        return None
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
    # Keep the previous setting until the complete new file is synced.
    temporary = path + ".tmp"
    with open(temporary, "w") as target:
        target.write("On\n" if enabled else "Off\n")
    os.sync()
    os.rename(temporary, path)
    os.sync()
    return True
