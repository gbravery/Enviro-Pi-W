import uasyncio as asyncio
import time
import network
import math
import rp2
import ubinascii
import config
from logger import log

# Link states derived from CYW43 architecture rules
CYW43_LINK_DOWN = 0
CYW43_LINK_JOIN = 1
CYW43_LINK_NOIP = 2
CYW43_LINK_UP = 3
CYW43_LINK_FAIL = -1
CYW43_LINK_NONET = -2
CYW43_LINK_BADAUTH = -3

status_names = {
    CYW43_LINK_DOWN: "Link is down",
    CYW43_LINK_JOIN: "Connected to wifi",
    CYW43_LINK_NOIP: "Connected to wifi, but no IP address",
    CYW43_LINK_UP: "Connected to wifi with an IP address",
    CYW43_LINK_FAIL: "Connection failed",
    CYW43_LINK_NONET: "No matching SSID found (could be out of range, or down)",
    CYW43_LINK_BADAUTH: "Authentication failure",
}

# Runtime tracking placeholders
wifi_mac_address = "unknown"
wifi_ip_address = "0.0.0.0"
wifi_connect_duration = 0.0

def dump_status(wlan):
    status = wlan.status()
    log("Comms:WiFi", f"WLAN interface state: {status} ({status_names.get(status, 'Unknown State')})")
    return status

async def wait_status_async(wlan, expected_status, timeout=10, tick_sleep=0.5):
    """Asynchronously polls the connection status without blocking the CPU."""
    iterations = math.ceil(timeout / tick_sleep)
    for _ in range(iterations):
        await asyncio.sleep(tick_sleep)  # Non-blocking pause; frees loop thread
        status = wlan.status()
        if status == expected_status:
            return True
        if status < 0:
            raise RuntimeError(status_names.get(status, "Unknown network driver failure."))
    return False

async def connect_async():
    global wifi_mac_address, wifi_ip_address, wifi_connect_duration
    start_ms = time.ticks_ms()

    ssid = getattr(config, "wifi_ssid", "DefaultSSID")
    password = getattr(config, "wifi_password", "")
    country = getattr(config, "wifi_country", "GB")
    
    try:
        import machine
        uid_suffix = ubinascii.hexlify(machine.unique_id()).decode()[-4:]
    except:
        uid_suffix = "W"
    hostname = getattr(config, "wifi_hostname", f"EnviroW-{uid_suffix}")

    log("Comms:WiFi", f"Configuring RF hardware profile for country: {country}...")
    rp2.country(country)
    network.hostname(hostname)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    vbus_present = getattr(config, "vbus_present", True) 
    if vbus_present:
        log("Comms:WiFi", "Power source detected on VBUS rails. Disabling CYW43 power saving mode.")
        wlan.config(pm=0xa11140)

    wifi_mac_address = ubinascii.hexlify(wlan.config('mac'), ':').decode()
    log("Comms:WiFi", f"Device hardware MAC Address: {wifi_mac_address}")

    status = wlan.status()
    if CYW43_LINK_JOIN <= status < CYW43_LINK_UP:
        log("Comms:WiFi", "Stale partial lease detected. Terminating transient link...")
        wlan.disconnect()
        try:
            await wait_status_async(wlan, CYW43_LINK_DOWN, timeout=3)
        except Exception as x:
            log("Comms:WiFi", f"Disconnect operation rejected: {x}", status="⚠️")

    log("Comms:WiFi", f"Negotiating physical link with base station SSID: '{ssid}'... 📡")
    wlan.connect(ssid, password)
    
    try:
        # Step 1: Wait until the hardware reports the link is up
        await wait_status_async(wlan, CYW43_LINK_UP, timeout=12)
    except Exception as err:
        log("Comms:WiFi", f"Infrastructure authentication aborted: {err}", status="❌")
        return False

    # Step 2: NEW DHCP LEASE VALIDATION LOOP
    # Force the async engine to wait until a valid IP layout is assigned by the router
    log("Comms:WiFi", "Link up. Verifying network layer configuration from DHCP...")
    dhcp_timeout_seconds = 5.0
    dhcp_start_ms = time.ticks_ms()
    
    while True:
        wifi_ip_address, subnet, gateway, dns = wlan.ifconfig()
        
        # If the IP is filled with a valid lease address, break out instantly
        if wifi_ip_address != "0.0.0.0":
            break
            
        # Check if the DHCP assignment has timed out to prevent battery drainage loops
        if time.ticks_diff(time.ticks_ms(), dhcp_start_ms) > (dhcp_timeout_seconds * 1000):
            log("Comms:WiFi", "Critical Error: Physical link established, but DHCP failed to lease an IP address.", status="❌")
            wlan.disconnect()
            return False
            
        # Yield control back to the scheduler for 100ms before querying the radio interfaces again
        await asyncio.sleep(0.1)

    # Step 3: Parse and print verified valid properties
    wifi_connect_duration = time.ticks_diff(time.ticks_ms(), start_ms)
    
    log("Comms:WiFi", f"Authenticated successfully! IP Address lease allocated: {wifi_ip_address}", status="✅")
    log("Comms:WiFi", f"Subnet: {subnet} | Gateway: {gateway} | DNS: {dns}")
    log("Comms:WiFi", f"Wi-Fi Connection handshake finalized in {wifi_connect_duration / 1000.0:.2f}s")
    
    if (wifi_connect_duration / 1000.0) > 5.0:
        log("Comms:WiFi", "Warning: Handshake exceeded 5 seconds. Excessive battery drain risk detected.", status="⚠️")
        
    return True
