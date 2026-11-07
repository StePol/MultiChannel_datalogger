import machine, onewire, ds18x20, sdcard, uos, ssd1306, time, ds3231, sht4x, ubinascii, gc

# Metadata is generated on the PC; manual deployments remain compatible.
try:
    from build_info import BUILD_VERSION, BUILD_GIT_SHA, BUILD_NUMBER, BUILD_DIRTY
except ImportError:
    BUILD_VERSION = "0.0.0-dev"
    BUILD_GIT_SHA = "unknown"
    BUILD_NUMBER = "0"
    BUILD_DIRTY = False

print("[BUILD INFO] version={} git={} build={}{}".format(
    BUILD_VERSION, BUILD_GIT_SHA, BUILD_NUMBER,
    " dirty" if BUILD_DIRTY else ""))


# --- KONFIGURÁCIA ---
# Uložený stav po štarte; bez platného nastavenia sa použije Off.
# True = ADS1256 AN0–AN7; False = pôvodné A1/A2 a B1–B4.
from input_settings import load_input_mode, save_input_mode
from input_settings import load_sample_count, save_sample_count, SAMPLE_OPTIONS
from input_settings import load_raw_mode, save_raw_mode, load_buffer_mode, save_buffer_mode
from input_settings import load_divider, save_divider
from adc_divider import DividerMenu, divider_label, divider_factor, measurement_range
from adc_divider import scale_values, voltage_label
ads_divider = load_divider()
ads_raw = load_raw_mode()
ads_buffer = load_buffer_mode()
ADS1256_ENABLED = load_input_mode()
ADS1256_VREF = 2.503  # Skutočne nameraná referencia modulu [V]
ADS1256_AVDD = 5.0  # Nominálne napájanie pre odhad rozsahu, nie meraná hodnota.
ADS1256_SCAN_MS = 1000
ADS1256_SAMPLE_OPTIONS = SAMPLE_OPTIONS
ads_samples = load_sample_count()  # Bez platného nastavenia 1 = bez priemerovania
from adc_average import ADCAverage
ads_average = ADCAverage(ads_samples, raw=ads_raw)
ads_collecting = False

TLACITKO_PIN = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
LED_EXT = machine.Pin(14, machine.Pin.OUT)
CS_SD = machine.Pin(17)
ads = None
ads_error = ""
ads_values = None
bin_vstupy = []
adc1 = adc2 = None


def set_input_mode(enabled):
    """Volá iba hlavná slučka pri vypnutom logovaní, nikdy IRQ."""
    global ADS1256_ENABLED, ads, ads_values, ads_error
    global bin_vstupy, adc1, adc2, ads_scan_timer, ads_average, ads_collecting
    # Ukončíme prístup ADC a uvoľníme spoločné GPIO pred novou konfiguráciou.
    if ads is not None:
        ads.cs.value(1)
    ads = None
    adc1 = adc2 = None
    bin_vstupy = []
    for gpio in (2, 3, 4, 5, 26, 27):
        machine.Pin(gpio, machine.Pin.IN)
    ads_values = None
    ads_error = ""
    ads_average = ADCAverage(ads_samples, raw=ads_raw)
    ads_collecting = False
    ADS1256_ENABLED = enabled
    if enabled:
        try:
            from ads1256 import ADS1256
            ads = ADS1256(vref=ADS1256_VREF, buffer_enabled=ads_buffer)
            print("Vstupy: ADS1256 AN0-AN7, VREF={} V, PGA=1, 100 SPS, buffer={}, RAW={}, SELFCAL OK".format(
                ADS1256_VREF, ads_buffer, ads_raw))
        except Exception as e:
            ads_error = str(e)
            print("ADS1256 INIT CHYBA:", e)
        # Pri chybe ponecháme zvolený režim; On v menu zopakuje inicializáciu.
    else:
        bin_vstupy = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in (2, 3, 4, 5)]
        adc1, adc2 = machine.ADC(26), machine.ADC(27)
        print("Vstupy: povodne A1/A2 a B1-B4")
    ads_scan_timer = time.ticks_add(time.ticks_ms(), -ADS1256_SCAN_MS)


set_input_mode(ADS1256_ENABLED)
pin_clk = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)
pin_dt = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
adc_bat = machine.ADC(28)
Batt_ctrl_pin = machine.Pin(21, machine.Pin.OUT)  # Ovládanie cez GP21

# --- INICIALIZÁCIA ---
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9))
spi = machine.SPI(0, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.write_cmd(0xA1); oled.write_cmd(0xC8)
from logo import show_startup
show_startup(oled, BUILD_VERSION)
rtc_ext = ds3231.DS3231(i2c)
senzor_sht = sht4x.SHT4X(i2c)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(machine.Pin(22)))

# --- SYNC A SD ---
try:
    t = rtc_ext.get_time()
    machine.RTC().datetime((t[0], t[1], t[2], 0, t[3], t[4], t[5], 0))
except: print("RTC Sync Fail")

sd_ready = False

def mount_sd():
    global sd_ready
    try:
        sd_inst = sdcard.SDCard(spi, CS_SD)
        vfs = uos.VfsFat(sd_inst)
        uos.mount(vfs, "/sd")
        sd_ready = True
        print("SD karta pripravena.")
    except:
        sd_ready = False

def check_sd():
    """Detekcia vytiahnutia/vloženia karty — volať len v PAUZA móde."""
    global sd_ready
    if sd_ready:
        try:
            # Pokus o listovanie root adresára — menej agresívne ako zápis
            uos.listdir("/sd")
        except:
            try: uos.umount("/sd")
            except: pass
            sd_ready = False
            print("SD karta vytiahnutá.")
    else:
        try:
            sd_inst = sdcard.SDCard(spi, CS_SD)
            vfs = uos.VfsFat(sd_inst)
            uos.mount(vfs, "/sd")
            sd_ready = True
            print("SD karta pripravená.")
        except:
            sd_ready = False

mount_sd()

def new_recording_filename(timestamp):
    # Aj dve spustenia v rovnakej sekunde musia mať oddelené CSV schémy.
    base = "/sd/{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(*timestamp)
    candidate = base + ".csv"
    suffix = 0
    while True:
        try:
            uos.stat(candidate)
        except OSError:
            return candidate
        suffix += 1
        candidate = base + "_{}.csv".format(suffix)


# --- PREMENNÉ ---
mode = "PAUZA"
# interval: -3 = Restart, -2 = SyncRTC, -1 = ADS1256, 0 = 1WIRE, 5-300 = zápis [s]
interval = 60
test_index = 0
ads_menu_choice = 0 if ADS1256_ENABLED else 1
settings_error = False
ads_sample_choice = 0
divider_menu = None
last_btn = 1
posledny_prevod_ds = 0
filename = ""
roms = ds_sensor.scan()
ds_v = [0.0] * len(roms)
st, sh = 0.0, 0.0
posledny_zapis_ms = time.ticks_ms()
loop_timer = time.ticks_ms()
sd_check_timer = time.ticks_ms()
SD_CHECK_INTERVAL = 5000  # Kontrola SD karty každých 5 sekúnd

# USB konzola: čítanie iba v hlavnej slučke, nikdy v IRQ.
from serial_commands import SerialCommands, HELP_LINES, configuration_lines
serial_console = SerialCommands()


def start_recording(source="SERIAL", refresh=True):
    global mode, filename, posledny_zapis_ms, roms, ds_v
    if mode == "REC":
        print("[OK] START already REC file={}".format(filename))
        return
    if mode != "PAUZA":
        print("[ERR] START mode={}; najprv opustite menu/TEST/SYNC".format(mode))
        return
    # IRQ nesmie medzi validáciou intervalu a prepnutím zmeniť výber.
    mode = "ADC_SWITCH"
    if interval not in range(5, 301, 5):
        mode = "PAUZA"
        print("[ERR] START vyberte interval 5-300 s v menu PAUZA")
        return
    try:
        if refresh:
            roms = ds_sensor.scan()
            ds_v = [0.0] * len(roms)
        candidate = new_recording_filename(time.localtime())
    except Exception as e:
        mode = "PAUZA"
        print("[ERR] START {}".format(e))
        return
    filename = candidate
    posledny_zapis_ms = time.ticks_ms()
    mode = "REC"
    print("[OK] START mode=REC source={} interval={}s file={} sd={}".format(
        source, interval, filename, "OK" if sd_ready else "NOT_READY"))


def stop_recording(source="SERIAL"):
    global mode
    if mode == "REC":
        # Každý zápis už uzatvára a synchronizuje súbor. Nemeníme konfiguráciu.
        mode = "PAUZA"
        print("[OK] STOP mode=PAUZA source={} file={}".format(source, filename))
    else:
        print("[OK] STOP already stopped mode={}".format(mode))


def serial_status():
    state = dict(version=BUILD_VERSION, sha=BUILD_GIT_SHA, build=BUILD_NUMBER,
                 dirty=BUILD_DIRTY, mode=mode, interval=interval, sd=sd_ready,
                 ds=len(roms), filename=filename, ads_enabled=ADS1256_ENABLED,
                 raw=ads_raw, samples=ads_samples, buffer=ads_buffer,
                 divider=ads_divider, vref=ADS1256_VREF, avdd=ADS1256_AVDD,
                 values_ready=ads_values is not None, ads_error=ads_error,
                 settings_error=settings_error)
    for line in configuration_lines(state):
        print(line)


def handle_serial_command(command):
    if command == "START":
        start_recording()
    elif command == "STOP":
        stop_recording()
    elif command == "RESET":
        if mode != "PAUZA":
            print("[ERR] RESET iba v PAUZA; pouzite STOP a opustite menu")
            return
        try:
            uos.sync()
        except OSError as e:
            print("[ERR] RESET sync failed: {}".format(e))
            return
        print("[OK] RESET restarting firmware")
        machine.reset()
    elif command == "STATUS":
        serial_status()
    elif command == "HELP":
        for line in HELP_LINES:
            print(line)
    elif command.startswith("!"):
        print("[ERR] {} limit=32 chars; pouzite HELP".format(command[1:]))
    else:
        print("[ERR] Neznamy prikaz; pouzite HELP")


print("[STATE] mode=PAUZA; serial: START STOP STATUS HELP RESET")

# --- ENKODÉR CEZ PRERUŠENIA ---
last_clk_state = pin_clk.value()

def encoder_handler(pin):
    global interval, test_index, mode, last_clk_state, ads_menu_choice, ads_sample_choice

    current_clk_state = pin_clk.value()
    # Vyhodnotíme len pri zmene stavu CLK
    if current_clk_state != last_clk_state:
        dt_state = pin_dt.value()

        # Smer otáčania: ak sa CLK líši od DT, ideme jedným smerom, inak druhým
        direction = 1 if dt_state != current_clk_state else -1

        if mode == "PAUZA":
            # Menu: Restart (-3) -> SyncRTC (-2) -> ADS1256 (-1) -> 1WIRE (0) -> 5s ... 300s
            if direction == -1:
                if interval > 5:    interval -= 5
                elif interval == 5: interval = 0    # 5s -> TEST
                elif interval == 0: interval = -1   # TEST -> ADS1256
                elif interval == -1: interval = -2  # ADS1256 -> SyncRTC
                elif interval == -2: interval = -3  # SyncRTC -> Restart
            else:
                if interval == -3:   interval = -2  # Restart -> SyncRTC
                elif interval == -2: interval = -1  # SyncRTC -> ADS1256
                elif interval == -1: interval = 0   # ADS1256 -> TEST
                elif interval == 0:  interval = 5   # TEST -> 5s
                elif interval < 300: interval += 5

        elif mode == "ADC_MENU":
            # Otáčanie iba vyberá; stlačenie potvrdí v hlavnej slučke.
            ads_menu_choice = max(0, min(6, ads_menu_choice + direction))

        elif mode == "ADC_DIVIDER":
            divider_menu.turn(direction)

        elif mode == "ADC_SAMPLES":
            ads_sample_choice = max(0, min(len(ADS1256_SAMPLE_OPTIONS) - 1,
                                          ads_sample_choice + direction))

        elif mode == "TEST" and roms:
            # Prepínanie senzorov v TEST móde
            test_index = (test_index + direction) % len(roms)

        last_clk_state = current_clk_state

# Nastavenie prerušení na oboch hranách CLK
pin_clk.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=encoder_handler)

if roms: ds_sensor.convert_temp()

from logger_csv import make_record

ads_scan_timer = time.ticks_add(time.ticks_ms(), -ADS1256_SCAN_MS)

# --- HLAVNÁ SLUČKA ---
while True:
    # 1. OPTIMALIZÁCIA PAMÄTE
    gc.collect()

    # Udržujeme stabilnú slučku cca 20Hz (50ms)
    if time.ticks_diff(time.ticks_ms(), loop_timer) < 50:
        continue
    loop_timer = time.ticks_ms()

    lt = time.localtime()
    cas_s = "{:02d}:{:02d}:{:02d}".format(lt[3], lt[4], lt[5])

    # 2. KONTROLA SD — len v PAUZA móde
    if mode == "PAUZA":
        if time.ticks_diff(time.ticks_ms(), sd_check_timer) > SD_CHECK_INTERVAL:
            check_sd()
            sd_check_timer = time.ticks_ms()

    # 3. OVLÁDANIE TLAČIDLA
    curr_btn = TLACITKO_PIN.value()
    if last_btn == 1 and curr_btn == 0:
        time.sleep_ms(50)
        if mode == "PAUZA":
            roms = ds_sensor.scan()
            ds_v = [0.0] * len(roms)
            if interval == -3:
                # Reštart len v PAUZA a v hlavnej slučke, nie v IRQ.
                uos.sync()
                machine.reset()
            elif interval == -1:
                ads_menu_choice = 0 if ADS1256_ENABLED else 1
                settings_error = False
                mode = "ADC_MENU"
            elif interval == -2:
                # Prechod do SYNC módu
                mode = "SYNC"
            elif interval == 0:
                # Prechod do TEST módu
                mode = "TEST"; test_index = 0
            else:
                start_recording("BUTTON", refresh=False)
        elif mode == "ADC_MENU":
            choice = ads_menu_choice
            if choice == 2:
                ads_sample_choice = ADS1256_SAMPLE_OPTIONS.index(ads_samples)
                mode = "ADC_SAMPLES"
            elif choice in (3, 4):
                mode = "ADC_SWITCH"
                if choice == 3:
                    ads_raw = not ads_raw
                else:
                    ads_buffer = not ads_buffer
                # Reinitialization discards old values and any unfinished batch.
                set_input_mode(ADS1256_ENABLED)
                try:
                    if choice == 3:
                        save_raw_mode(ads_raw)
                    else:
                        save_buffer_mode(ads_buffer)
                    settings_error = False
                except OSError as e:
                    print("ADS NASTAVENIE ULOZENIE CHYBA:", e)
                    settings_error = True
                mode = "ADC_MENU"
            elif choice == 5:
                divider_menu = DividerMenu(ads_divider)
                mode = "ADC_DIVIDER"
            elif choice == 6:
                mode = "PAUZA"
            else:
                mode = "ADC_SWITCH"
                set_input_mode(choice == 0)
                try:
                    save_input_mode(ADS1256_ENABLED)
                    settings_error = False
                    mode = "PAUZA"
                except OSError as e:
                    print("NASTAVENIE ULOZENIE CHYBA:", e)
                    settings_error = True
                    mode = "ADC_MENU"
        elif mode == "ADC_DIVIDER":
            mode = "ADC_SWITCH"
            action = divider_menu.press()
            if action == "apply":
                mode = "ADC_SWITCH"
                ads_divider = divider_menu.config
                # No old result or unfinished batch may survive a scale change.
                ads_average = ADCAverage(ads_samples, raw=ads_raw)
                ads_collecting = False
                ads_values = None
                ads_scan_timer = time.ticks_add(time.ticks_ms(), -ADS1256_SCAN_MS)
                try:
                    save_divider(ads_divider)
                    settings_error = False
                except OSError as e:
                    print("DELIC ULOZENIE CHYBA:", e)
                    settings_error = True
                print("ADS1256 {} K={} rozsah=0-{} V".format(
                    divider_label(ads_divider, ads_buffer),
                    divider_factor(ads_divider, ads_buffer),
                    measurement_range(ads_divider, ads_buffer, ADS1256_AVDD, ADS1256_VREF)))
                mode = "ADC_MENU"
            elif action == "cancel":
                mode = "ADC_MENU"
            else:
                mode = "ADC_DIVIDER"
        elif mode == "ADC_SAMPLES":
            mode = "ADC_SWITCH"
            ads_samples = ADS1256_SAMPLE_OPTIONS[ads_sample_choice]
            ads_average = ADCAverage(ads_samples, raw=ads_raw)
            ads_collecting = False
            ads_values = None  # Nemiešať výsledky starého a nového nastavenia.
            ads_scan_timer = time.ticks_add(time.ticks_ms(), -ADS1256_SCAN_MS)
            print("ADS1256 priemerovanie: {} vzoriek/kanal".format(ads_samples))
            try:
                save_sample_count(ads_samples)
                settings_error = False
            except OSError as e:
                print("VZORKY ULOZENIE CHYBA:", e)
                settings_error = True
            mode = "ADC_MENU"
        elif mode == "REC":
            stop_recording("BUTTON")
        else:
            mode = "PAUZA"
        LED_EXT.value(1); time.sleep_ms(100); LED_EXT.value(0)
    last_btn = curr_btn

    # Najviac jeden príkaz/64 znakov za slučku; nečakáme na koniec riadka.
    command = serial_console.read_command()
    if command is not None:
        handle_serial_command(command)

    # 4. MERANIE
    try: st, sh = senzor_sht.measurements()
    except: st, sh = -99.9, -99.9

    Batt_ctrl_pin.value(1)        # Otvorí BS170 -> zopne BSS84
    v_bat = round((adc_bat.read_u16() * 3.3) / 65535, 2) * 2
    Batt_ctrl_pin.value(0)        # Okamžite odpojí delič (nulová spotreba)

    if ADS1256_ENABLED:
        if ads is not None and (ads_collecting or
                time.ticks_diff(time.ticks_ms(), ads_scan_timer) >= ADS1256_SCAN_MS):
            ads_collecting = True
            try:
                # Jeden čerstvý prevod na slučku; tlačidlo zostáva obsluhované.
                result = ads_average.step(ads)
                if result is not None:
                    ads_values = scale_values(result, ads_raw, ads_divider, ads_buffer)
                    ads_error = ""
                    ads_collecting = False
                    ads_scan_timer = time.ticks_ms()
            except Exception as e:
                ads_values = None
                ads_average = ADCAverage(ads_samples, raw=ads_raw)
                ads_collecting = False
                ads_error = str(e)
                print("ADS1256 MERANIE CHYBA:", e)
                ads_scan_timer = time.ticks_ms()
    else:
        v1 = round((adc1.read_u16() * 3.3) / 65535, 2)
        v2 = round((adc2.read_u16() * 3.3) / 65535, 2)
        bin_s = "".join(["0" if p.value() == 0 else "1" for p in bin_vstupy])

    if roms and time.ticks_diff(time.ticks_ms(), posledny_prevod_ds) > 800:
        try:
            ds_v = [round(ds_sensor.read_temp(r), 2) for r in roms]
            ds_sensor.convert_temp()
            posledny_prevod_ds = time.ticks_ms()
        except: pass

    # 5. DISPLEJ A LOGIKA ZÁPISU
    oled.fill(0)
    # Podmenu má vlastný nadpis cez celý riadok; čas patrí na hlavné obrazovky.
    if mode not in ("ADC_MENU", "ADC_SAMPLES", "ADC_DIVIDER"):
        oled.text(cas_s, 64, 0)

    if mode == "PAUZA":
        oled.text("STOP", 0, 0)
        # Zobrazenie aktuálne zvolenej položky menu
        if interval == -3:  label = "Restart"
        elif interval == -2: label = "SyncRTC"
        elif interval == -1: label = "ADS1256"
        elif interval == 0: label = "1WIRE"
        else:               label = "{}s".format(interval)
        oled.text("Int: {}".format(label), 0, 12)

    elif mode == "ADC_MENU":
        oled.text("Ulozenie CHYBA" if settings_error else
                  "ADS1256 " + ("On" if ADS1256_ENABLED else "Off"), 0, 0)
        labels = ("On", "Off", "Vzorky: {}".format(ads_samples),
                  "RAW: " + ("On" if ads_raw else "Off"),
                  "Imp:" + ("Hi(3V)" if ads_buffer else "Lo(5V)"),
                  divider_label(ads_divider, ads_buffer), "Spat")
        first = max(0, ads_menu_choice - 3)
        for row, index in enumerate(range(first, min(first + 4, len(labels)))):
            active = (index == 0 and ADS1256_ENABLED) or (index == 1 and not ADS1256_ENABLED)
            oled.text(("> " if index == ads_menu_choice else "  ") + labels[index] +
                      (" [AKT]" if active else ""), 0, 14 + row * 12)

    elif mode == "ADC_DIVIDER":
        divider_menu.draw(oled, ads_buffer, ADS1256_AVDD, ADS1256_VREF)

    elif mode == "ADC_SAMPLES":
        oled.text("ADS1256 Vzorky", 0, 0)
        oled.text("N: {} / kanal".format(ADS1256_SAMPLE_OPTIONS[ads_sample_choice]), 0, 20)
        if ads_raw:
            oled.text("RAW pouziva N=1", 0, 32)
        oled.text("Stlac = potvrdit", 0, 42)

    elif mode == "SYNC":
        # Synchronizácia RTC podľa interných hodín Pico (nastavených Thonny pri spustení)
        oled.text("SYNC RTC", 0, 0)
        oled.text("Synchronizujem...", 0, 24)
        oled.show()
        try:
            t = time.localtime()
            rtc_ext.datetime((t[0], t[1], t[2], t[3], t[4], t[5], t[6]))
            machine.RTC().datetime((t[0], t[1], t[2], 0, t[3], t[4], t[5], 0))
            print("------------------------------------------")
            print("RTC zosynchronizovany s PC!")
            print("Aktuálny čas: {:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5]))
            print("------------------------------------------")
            oled.fill(0)
            oled.text("SYNC RTC", 0, 0)
            oled.text("OK!", 0, 24)
            oled.text("{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5]), 0, 40)
            oled.show()
        except Exception as e:
            print("SYNC CHYBA:", e)
            oled.fill(0)
            oled.text("SYNC CHYBA!", 0, 24)
            oled.show()
        time.sleep_ms(2000)
        mode = "PAUZA"

    elif mode == "TEST":
        oled.text("1WIRE", 0, 0)
        if roms:
            fa = ubinascii.hexlify(roms[test_index]).decode()
            oled.text("Senzor: {}/{}".format(test_index + 1, len(roms)), 0, 12)
            oled.text("ID: {}".format(fa[:8]), 0, 24)
            oled.text("    {}".format(fa[8:]), 0, 34)
            oled.text("Teplota: {}C".format(ds_v[test_index] if test_index < len(ds_v) else "--"), 0, 48)
        else:
            oled.text("Ziadne senzory!", 0, 24)

    elif mode == "REC":
        if int(time.time()) % 2: oled.text("REC", 0, 0)

        # Výpočet času do ďalšieho zápisu
        ms_od_zapisu = time.ticks_diff(time.ticks_ms(), posledny_zapis_ms)
        sek_do = max(0, interval - (ms_od_zapisu // 1000))
        oled.text("Ct: {}s".format(int(sek_do)), 0, 12)

        if ms_od_zapisu >= (interval * 1000):
            # --- TERMINÁL VÝPIS ---
            print("\n" + "=" * 50)
            if ADS1256_ENABLED:
                print("ZAPIS [{}] ADS1256: {}".format(cas_s, ads_values if ads_values is not None else ads_error))
            else:
                print("ZAPIS [{}] SHT:{:.1f}C {:.1f}% ADC:{}V {}V BIN:{}".format(
                    cas_s, st, sh, v1, v2, bin_s))
            for i, r in enumerate(roms):
                print("  DS #{}: [{}] -> {}C".format(i + 1, ubinascii.hexlify(r).decode(), ds_v[i]))

            # --- ZÁPIS NA SD ---
            if sd_ready:
                try:
                    # Zisťujeme, či súbor existuje (ak nie, musíme zapísať hlavičku)
                    try: uos.stat(filename); subor_existuje = True
                    except: subor_existuje = False

                    with open(filename, "a") as f:
                        header, data_row = make_record(
                            cas_s, st, sh, v_bat,
                            [ubinascii.hexlify(r).decode() for r in roms], ds_v,
                            ADS1256_ENABLED, ads_values,
                            None if ADS1256_ENABLED else (v1, v2),
                            None if ADS1256_ENABLED else bin_s, ads_raw=ads_raw)
                        if not subor_existuje:
                            f.write(header)
                            print("-> Vytvorena hlavicka s ID.")
                        f.write(data_row)
                        f.flush()
                        uos.sync()
                    print("-> Ulozene na SD: " + filename)
                except Exception as e:
                    print("-> CHYBA ZAPISU:", e)
                    sd_ready = False

            LED_EXT.value(1); time.sleep_ms(50); LED_EXT.value(0)
            posledny_zapis_ms = time.ticks_ms()

    # 6. SPODNÝ RIADOK DISPLEJA — merania (nie v TEST a SYNC móde)
    if mode not in ("TEST", "SYNC", "ADC_MENU", "ADC_SAMPLES", "ADC_DIVIDER"):
        oled.text("SHT: {:.1f}C {:.0f}%".format(st, sh), 0, 24)
        if ADS1256_ENABLED:
            if ads_values is None:
                oled.text("ADS1256 CHYBA" if ads_error else "ADS meranie...", 0, 34)
            else:
                ch = (time.ticks_ms() // 2000) % 8
                oled.text(("RAW{}: {}".format(ch, int(ads_values[ch])) if ads_raw else
                           voltage_label(ch, ads_values[ch])), 0, 34)
            oled.text("DS: {}".format(len(roms)), 0, 44)
        else:
            oled.text("ADC: {:.2f}V {:.2f}V".format(v1, v2), 0, 34)
            oled.text("DS: {} BIN: {}".format(len(roms), bin_s), 0, 44)
        try:
            if sd_ready:
                fs = uos.statvfs("/sd")
                oled.text("SD:{:.2f}GB".format((fs[0] * fs[3]) / (1024 ** 3)), 0, 54)
            else:
                oled.text("SD:none", 0, 54)
        except:
            oled.text("SD:err", 0, 54)
        oled.text(">{:.2f}V".format(v_bat), 80, 54)

    oled.show()
    time.sleep_ms(10)
