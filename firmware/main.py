import machine, onewire, ds18x20, sdcard, uos, ssd1306, time, ds3231, sht4x, ubinascii, gc

# --- KONFIGURÁCIA ---
TLACITKO_PIN = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
LED_EXT = machine.Pin(14, machine.Pin.OUT)
CS_SD = machine.Pin(17)
bin_vstupy = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in (2, 3, 4, 5)]
pin_clk = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)
pin_dt = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
adc1, adc2 = machine.ADC(26), machine.ADC(27)
adc_bat = machine.ADC(28)
Batt_ctrl_pin = machine.Pin(21, machine.Pin.OUT)  # Ovládanie cez GP21

# --- INICIALIZÁCIA ---
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9))
spi = machine.SPI(0, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.write_cmd(0xA1); oled.write_cmd(0xC8)
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

# --- PREMENNÉ ---
mode = "PAUZA"
# interval: -1 = SyncRTC, 0 = TEST, 5-300 = interval zápisu v sekundách
interval = 60
test_index = 0
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

# --- ENKODÉR CEZ PRERUŠENIA ---
last_clk_state = pin_clk.value()

def encoder_handler(pin):
    global interval, test_index, mode, last_clk_state

    current_clk_state = pin_clk.value()
    # Vyhodnotíme len pri zmene stavu CLK
    if current_clk_state != last_clk_state:
        dt_state = pin_dt.value()

        # Smer otáčania: ak sa CLK líši od DT, ideme jedným smerom, inak druhým
        direction = 1 if dt_state != current_clk_state else -1

        if mode == "PAUZA":
            # Menu: SyncRTC (-1) -> TEST (0) -> 5s -> 10s -> ... -> 300s
            if direction == -1:
                if interval > 5:    interval -= 5
                elif interval == 5: interval = 0    # 5s -> TEST
                elif interval == 0: interval = -1   # TEST -> SyncRTC
            else:
                if interval == -1:   interval = 0   # SyncRTC -> TEST
                elif interval == 0:  interval = 5   # TEST -> 5s
                elif interval < 300: interval += 5

        elif mode == "TEST" and roms:
            # Prepínanie senzorov v TEST móde
            test_index = (test_index + direction) % len(roms)

        last_clk_state = current_clk_state

# Nastavenie prerušení na oboch hranách CLK
pin_clk.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=encoder_handler)

if roms: ds_sensor.convert_temp()

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
            if interval == -1:
                # Prechod do SYNC módu
                mode = "SYNC"
            elif interval == 0:
                # Prechod do TEST módu
                mode = "TEST"; test_index = 0
            else:
                # Prechod do REC módu — vytvorí nový súbor s časovou pečiatkou
                mode = "REC"
                posledny_zapis_ms = time.ticks_ms()
                filename = "/sd/{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}.csv".format(*lt)
        else:
            mode = "PAUZA"
        LED_EXT.value(1); time.sleep_ms(100); LED_EXT.value(0)
    last_btn = curr_btn

    # 4. MERANIE
    try: st, sh = senzor_sht.measurements()
    except: st, sh = -99.9, -99.9

    Batt_ctrl_pin.value(1)        # Otvorí BS170 -> zopne BSS92
    v1 = round((adc1.read_u16() * 3.3) / 65535, 2)
    v2 = round((adc2.read_u16() * 3.3) / 65535, 2)
    v_bat = round((adc_bat.read_u16() * 3.3) / 65535, 2) * 2
    Batt_ctrl_pin.value(0)        # Okamžite odpojí delič (nulová spotreba)

    bin_s = "".join(["0" if p.value() == 0 else "1" for p in bin_vstupy])

    if roms and time.ticks_diff(time.ticks_ms(), posledny_prevod_ds) > 800:
        try:
            ds_v = [round(ds_sensor.read_temp(r), 2) for r in roms]
            ds_sensor.convert_temp()
            posledny_prevod_ds = time.ticks_ms()
        except: pass

    # 5. DISPLEJ A LOGIKA ZÁPISU
    oled.fill(0)
    oled.text(cas_s, 64, 0)

    if mode == "PAUZA":
        oled.text("STOP", 0, 0)
        # Zobrazenie aktuálne zvolenej položky menu
        if interval == -1:  label = "SyncRTC"
        elif interval == 0: label = "TEST"
        else:               label = "{}s".format(interval)
        oled.text("Int: {}".format(label), 0, 12)

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
        oled.text("TEST", 0, 0)
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
                        # Ak súbor neexistoval, zapíšeme hlavičku s ID senzormi
                        if not subor_existuje:
                            ids = ",".join([ubinascii.hexlify(r).decode() for r in roms])
                            f.write("Cas,SHT_T,SHT_H,A1,A2,BIN,B1,B2,B3,B4,{}\n".format(ids))
                            print("-> Vytvorena hlavicka s ID.")
                        data_row = "{},{:.2f},{:.1f},{:.2f},{:.2f},{},{},{}\n".format(
                            cas_s, st, sh, v1, v2, bin_s,
                            ",".join([c for c in bin_s]),
                            ",".join(map(str, ds_v))
                        )
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
    if mode not in ("TEST", "SYNC"):
        oled.text("SHT: {:.1f}C {:.0f}%".format(st, sh), 0, 24)
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