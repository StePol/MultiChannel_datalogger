"""Bounded, nonblocking USB-console command input; no configuration writes."""


class SerialCommands:
    def __init__(self, stream=None, poller=None):
        if stream is None:
            import sys
            stream = sys.stdin
        if poller is None:
            import select
            poller = select.poll()
            poller.register(stream, select.POLLIN)
        self.stream = stream
        self.poller = poller
        self.buffer = ""
        self.error = None

    def read_command(self, budget=64):
        # One command and at most budget characters per main-loop iteration.
        for _ in range(budget):
            try:
                events = self.poller.poll(0)
                if not events:
                    return None
                if not events[0][1] & 1:  # POLLIN; don't read on HUP/ERR alone
                    self.buffer = ""
                    self.error = None
                    return None
                char = self.stream.read(1)
            except OSError:
                self.buffer = ""
                self.error = None
                return None
            if not char:
                self.buffer = ""
                self.error = None
                return None
            if char in ("\r", "\n"):
                command = self.error or self.buffer.strip().upper()
                self.buffer = ""
                self.error = None
                if command:
                    return command
            elif self.error is not None:
                continue  # discard the complete damaged line, never its suffix
            elif char in ("\b", "\x7f"):
                self.buffer = self.buffer[:-1]
            elif char == "\t" or 32 <= ord(char) <= 126:
                if len(self.buffer) >= 32:
                    self.error = "!LINE_TOO_LONG"
                    self.buffer = ""
                else:
                    self.buffer += char
            else:
                self.error = "!INVALID_CHARACTER"
                self.buffer = ""
        return None


HELP_LINES = (
    "[HELP] START  - spusti REC z PAUZA pri zvolenom intervale 5-300 s",
    "[HELP] STOP   - zastavi REC, meranie a zobrazovanie pokracuju",
    "[HELP] STATUS - vypise aktualny stav a konfiguraciu",
    "[HELP] HELP   - vypise pouzitie prikazov",
    "[HELP] RESET  - synchronizuje ulozisko a restartuje Pico iba v PAUZA",
    "[HELP] Prikaz ukoncite Enter (CR/LF), velkost pismen nerozhoduje.",
    "[HELP] Nastavenia iba cez menu. START v menu/TEST/SYNC sa odmietne.",
    "[HELP] STOP mimo REC nemeni menu ani jeho rozpracovane nastavenia.",
    "[HELP] Ctrl-C prerusi program do REPL; nie je to prikaz STOP.",
)


def configuration_lines(state):
    from adc_divider import divider_factor, measurement_range, input_impedance
    config = state["divider"]
    enabled, rgnd, rin = config
    high = state["buffer"]
    raw = state["raw"]
    adc_enabled = state["ads_enabled"]
    factor = divider_factor(config, high)
    interval = state["interval"]
    selection = ("{}s".format(interval) if interval > 0 else
                 {-3: "Restart", -2: "SyncRTC", -1: "ADS1256", 0: "1WIRE"}.get(interval, "invalid"))
    return (
        "[STATUS] FW={} git={} build={} dirty={}".format(
            state["version"], state["sha"], state["build"], state["dirty"]),
        "[STATUS] mode={} interval_selection={} sd={} ds={}".format(
            state["mode"], selection, "OK" if state["sd"] else "NOT_READY", state["ds"]),
        "[STATUS] file={}".format(state["filename"] or "-"),
        "[STATUS] inputs={} RAW={} samples_saved={} samples_effective={}".format(
            "ADS1256" if adc_enabled else "A1/A2+B1-B4", raw, state["samples"],
            (1 if raw else state["samples"]) if adc_enabled else "N/A"),
        "[STATUS] ADS config: Imp={} Zadc={}Ohm PGA=1 DRATE=100SPS VREF={}V AVDD_nom={}V".format(
            "Hi(3V)" if high else "Lo(5V)", input_impedance(high), state["vref"], state["avdd"]),
        "[STATUS] ADS divider: enabled={} Rgnd={}Ohm Rin={}Ohm K={:.8g} range_nom=0-{:.8g}V".format(
            enabled, rgnd, rin, factor, measurement_range(config, high, state["avdd"], state["vref"])),
        "[STATUS] ADS output={} data={} error={}".format(
            ("RAW codes" if raw else "Uin[V]" if enabled else "Uadc[V]") if adc_enabled else "inactive",
            "READY" if state["values_ready"] else "UNAVAILABLE", state["ads_error"] or "-"),
        "[STATUS] settings_save_error={} (ADS config is inactive when ADS Off)".format(state["settings_error"]),
        "[STATUS] END",
    )
