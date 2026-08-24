import config
import uasyncio as asyncio
import socket
import ntptime
import time
import event_bus  # Neutral event framework
from logger import log

async def sync_async():
    """Asynchronously handles network clock lookups using native ntptime sockets."""
    log("Comms:NTP", "Initiating network time validation sequence...")
    
    ntptime.host = getattr(config, "ntp_server", "pool.ntp.org")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(4.0)
        
        log("Comms:NTP", f"Querying timeserver host: {ntptime.host} via UDP port 123...")
        await asyncio.sleep(0.01)
        ntptime.settime() 
        
        lt = time.localtime()
        timestamp = (lt[0], lt[1], lt[2], lt[6], lt[3], lt[4], lt[5], 0)
        
        # Publish the raw timestamp array to the bus so the hardware layer can capture it
        event_bus.publish("time:received", timestamp)
        return True
        
    except OSError as e:
        log("Comms:NTP", f"Network timing authority rejected packet request: {e}", status="⚠️")
    except Exception as err:
        log("Comms:NTP", f"Unexpected runtime error during NTP handshake: {err}", status="❌")
        
    return False
