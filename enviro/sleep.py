import os
import sys
import time
import config
import uasyncio as asyncio
from machine import Pin
from logger import log, get_current_timezone_offset

# Pull core pinouts and states from constants module
from enviro.constants import HOLD_VSYS_EN_PIN, WARN_LED_BLINK, WARN_LED_OFF
from .clock import rtc_chip, i2c

def is_usb_powered():
    """Tracks if the device is currently drawing power over VBUS USB lines."""
    return getattr(config, "vbus_present", True)

def calculate_next_alarm(interval_minutes):
    """Calculates target hour and minute indexes for the next wake cycle in pure UTC."""
    lt = time.localtime()
    current_hour, current_minute = lt[3], lt[4]
    
    total_minutes = current_minute + int(interval_minutes)
    target_minute = total_minutes % 60
    hours_to_advance = total_minutes // 60
    target_hour = (current_hour + hours_to_advance) % 24
    
    return target_hour, target_minute

def configure_hardware_sleep():
    """Safely updates physical alarm registers and determines power route."""
    interval = getattr(config, "reading_frequency", 15)
    utc_alarm_h, alarm_m = calculate_next_alarm(interval)
    
    # Calculate local time representation for the log display
    utc_epoch_now = time.time()
    offset_hours = get_current_timezone_offset(utc_epoch_now)
    local_alarm_h = (utc_alarm_h + offset_hours) % 24
    
    ampm = "pm" if local_alarm_h >= 12 else "am"
    display_h = local_alarm_h % 12
    if display_h == 0: display_h = 12
        
    log("Enviro:Sleep", f"Programming hardware wake alarm for {display_h:02d}:{alarm_m:02d}{ampm} Local (24h UTC: {utc_alarm_h:02d}:{alarm_m:02d})")
    
    try:
        # Program the physical registers using the exact positional format (minute, hour)
        rtc_chip.set_alarm(utc_alarm_h, alarm_m)
        rtc_chip.enable_alarm_interrupt(True)
    except Exception as e:
        log("Enviro:Sleep", f"Critical hardware register modification failed: {e}", status="❌")

    try:
        if "watchdog_live.txt" in os.listdir():
            os.remove("watchdog_live.txt")
    except Exception as e:
        log("Enviro:Sleep", f"Watchdog clear skipped: {e}", status="⚠️")

    if is_usb_powered():
        log("Enviro:Sleep", "USB power active. Handing control to the Chassis sleep engine... 🔌")
        import event_bus
        event_bus.publish("system:sleep_active")
        return
        
    log("Enviro:Sleep", "Dropping HOLD_VSYS_EN rail voltage. Initiating deep battery sleep state... 💤")
    hold_vsys = Pin(HOLD_VSYS_EN_PIN, Pin.OUT, value=0)
    while True:
        hold_vsys.value(0)
        time.sleep_ms(10)
