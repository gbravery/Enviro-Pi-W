import json
from logger import log
import os

READINGS_DIR = "readings"

def ensure_directory():
    try:
        os.mkdir(READINGS_DIR)
    except OSError:
        pass  # Already exists

def save_to_cache(data):
    ensure_directory()
    # Generate a unique filename using milliseconds or standard timestamps
    import time
    filename = f"{READINGS_DIR}/{time.ticks_ms()}.json"
    
    log("Enviro:Storage", "Caching telemetry structure to local flash storage...")
    with open(filename, "w") as f:
        json.dump(data, f)
    log("Enviro:Storage", "Data structural write completed.", status="💾")
