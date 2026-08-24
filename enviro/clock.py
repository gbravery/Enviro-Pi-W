import os
import time
import config
from machine import Pin, RTC, I2C
from pcf85063a import PCF85063A

# Pull the I2C hardware pin mappings AND the Warning State constants directly from your file
from enviro.constants import (
    I2C_SDA_PIN, 
    I2C_SCL_PIN, 
    WARN_LED_OFF, 
    WARN_LED_ON, 
    WARN_LED_BLINK
)
from logger import log

# Initialize shared I2C bus and the external real-time clock chip
i2c = I2C(0, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN), freq=400000)
rtc_chip = PCF85063A(i2c)

# Ensure external hardware RTC oscillator is actively running
i2c.writeto_mem(0x51, 0x00, b'\x00')
rtc_chip.enable_timer_interrupt(False)

# Explicitly default the warning LED to OFF on boot
i2c.writeto_mem(0x51, 0x00, b'\x00')

def set_warn_led(state):
    """Sets the physical state of the red warning LED via the RTC clock output register."""
    if state == WARN_LED_OFF:
        rtc_chip.set_clock_output(PCF85063A.CLOCK_OUT_OFF)
    elif state == WARN_LED_ON:
        rtc_chip.set_clock_output(PCF85063A.CLOCK_OUT_1024HZ)
    elif state == WARN_LED_BLINK:
        rtc_chip.set_clock_output(PCF85063A.CLOCK_OUT_1HZ)

# Turn warning LED off initially to clear default 32KHz factory frequency
set_warn_led(WARN_LED_OFF)

def sync_pico_internal_rtc():
    """Mirrors the external PCF85063A clock directly to the RP2040 internal RTC."""
    try:
        t = rtc_chip.datetime()
        # Format mapping: (year, month, day, weekday, hour, minute, second, subseconds)
        # Prevents EINVAL (Errno 22) errors by writing safe structural parameters
        RTC().datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
    except Exception as e:
        log("Enviro:Clock", f"Pico internal RTC register mirror failed: {e}", status="⚠️")

# Run an initial cross-sync instantly when the module loads
sync_pico_internal_rtc()

def is_clock_set():
    """Validates if the hardware clock configuration is trusted and un-drifted."""
    try:
        current_year = rtc_chip.datetime()[0]
        if current_year <= 2020 or current_year >= 2050:
            return False
    except:
        return False

    # Check local sync history log file
    try:
        os.stat("sync_time.txt")
    except OSError:
        return False # No sync history file exists

    try:
        # Simplistic lightweight replacement parsing loop for helpers structures
        with open("sync_time.txt", "r") as f:
            first_line = f.readline().strip()
            if not first_line:
                return False
                
        # Parse timestamp into a comparable tuple format
        # Expects: YYYY-MM-DDTHH:MM:SSZ
        year = int(first_line[0:4])
        month = int(first_line[5:7])
        day = int(first_line[8:10])
        hour = int(first_line[11:13])
        minute = int(first_line[14:16])
        second = int(first_line[17:19]) if len(first_line) >= 19 else 0
        
        last_sync_secs = time.mktime((year, month, day, hour, minute, second, 0, 0))
        current_secs = time.time()
        
        seconds_since_sync = current_secs - last_sync_secs
        max_allowed_delta = int(getattr(config, "resync_frequency", 24)) * 60 * 60
        
        if 0 <= seconds_since_sync < max_allowed_delta:
            return True
            
        log("Enviro:Clock", f"RTC sync threshold expired (> {config.resync_frequency} hrs)")
    except Exception as e:
        log("Enviro:Clock", f"Failed to parse synchronization tracker logs: {e}", status="⚠️")
        
    return False

def commit_ntp_timestamp(timestamp):
    """Safely updates physical hardware and logs the transaction."""
    try:
        # Reset control registers to ensure clock updates safely
        i2c.writeto_mem(0x51, 0x00, b'\x10')
        rtc_chip.datetime(timestamp)
        i2c.writeto_mem(0x51, 0x00, b'\x00')
        rtc_chip.enable_timer_interrupt(False)
        
        # Cross-mirror to internal RP2040 registers immediately
        sync_pico_internal_rtc()
        
        # Write out standard ISO-8601 formatting trace
        with open("sync_time.txt", "w") as syncfile:
            syncfile.write("{0:04d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}Z".format(*timestamp))
        return True
    except Exception as e:
        log("Enviro:Clock", f"Failed to write fresh time mapping to hardware registers: {e}", status="❌")
        return False
