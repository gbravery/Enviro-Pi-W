import os
import config
from machine import Pin, RTC
from rp2 import PIO, StateMachine, asm_pio
from .constants import HOLD_VSYS_EN_PIN
from logger import log

@asm_pio(sideset_init=PIO.OUT_HIGH)
def delayoff_prog():   
    label('d_loop')
    jmp(y_dec, 'd_loop')
    label('done')
    jmp('done').side(0)

class DELAYOFF:
    def __init__(self, pin, delay_minutes, sm_id=0):
        delay_ms = int(delay_minutes * 60 * 1000)
        self._sm = StateMachine(sm_id, delayoff_prog, freq=2000, sideset_base=Pin(pin))
        self._sm.put(delay_ms)
        self._sm.exec('pull()')
        self._sm.exec("mov(y, osr)")
        self._sm.active(1)
        log("Enviro:Watchdog", f"PIO hardware timer armed on GPIO {pin} for {delay_ms} ms")

def file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def arm():
    log("Enviro:Watchdog", "Arming crash protection systems...")
    if file_exists("watchdog_live.txt"):
        try:
            os.remove("watchdog_live.txt")
            log("Enviro:Watchdog", "Recovered from a previous hang!", status="⚠️")
        except OSError:
            pass

    try:
        rtc = RTC()
        dt = rtc.datetime()
        hour, minute, second = dt[4:7] 
        minute += int(config.pio_watchdog_time) + 1
        if second > 55:
            minute += 1

        while minute >= 60:      
            minute -= 60
            hour += 1
        if hour >= 24:
            hour -= 24
        log("Enviro:Watchdog", f"Backup RTC alarm set for {hour:02}:{minute:02}")
    except Exception as e:
        log("Enviro:Watchdog", f"RTC alarm failed: {e}", status="❌")

    global _hardware_watchdog
    _hardware_watchdog = DELAYOFF(HOLD_VSYS_EN_PIN, int(config.pio_watchdog_time))
    
    with open("watchdog_live.txt", "w") as hangfile:
        hangfile.write("")
    log("Enviro:Watchdog", "Flash hang-file written. Fully armed.", status="🛡️")

def disarm():
    if file_exists("watchdog_live.txt"):
        try:
            os.remove("watchdog_live.txt")
            log("Enviro:Watchdog", "Clean cycle completed. Disarmed.", status="✅")
        except OSError:
            pass
