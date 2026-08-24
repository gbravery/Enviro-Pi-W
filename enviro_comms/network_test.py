import uasyncio as asyncio
import network
from logger import log
from . import wifi, ntp

async def verify_network_and_ntp(enviro_device):
    log("Test:Network", "--- Initiating Live Infrastructure Diagnostics ---")
    
    enviro_device.set_warning_led(enviro_device.clock.WARN_LED_BLINK)
    wifi_connected = await wifi.connect_async()
    
    if wifi_connected:
        enviro_device.pulse_green()
        log("Test:Network", "Wi-Fi link verified. Directing ntp sub-module to fetch network time...")
        ntp_success = await ntp.sync_async()
        
        if ntp_success:
            log("Test:Network", "Live NTP transaction confirmed functional.", status="🛰️")
        else:
            log("Test:Network", "Wi-Fi works, but NTP request was rejected or timed out.", status="⚠️")
            
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.disconnect()
            log("Test:Network", "Cleanly severed testing Wi-Fi link lease.")
        except:
            pass
    else:
        log("Test:Network", "Critical Error: Wi-Fi driver failed to establish connection.", status="❌")
        
    enviro_device.set_warning_led(enviro_device.clock.WARN_LED_OFF)
    log("Test:Network", "Infrastructure diagnostics completed.")
