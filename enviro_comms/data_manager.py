import uasyncio as asyncio
from logger import log
import time

_start = time.ticks_ms()
def log(msg):
    elapsed = time.ticks_diff(time.ticks_ms(), _start) / 1000.0
    print(f"[+{elapsed:4.2f}s] [Storage] {msg}")

_local_cache = []

def save_to_cache(data):
    log("Saving reading to local flash cache...")
    _local_cache.append(data)
    log("Data cached safely. ✅")

async def upload_cached_data():
    if not _local_cache:
        log("No cached data to upload.")
        return
    
    log(f"Found {len(_local_cache)} items in cache. Preparing MQTT upload...")
    await asyncio.sleep(0.5)  # Network latency simulation
    log("All cached data published to MQTT successfully! 🚀")
    _local_cache.clear()
