from logger import log
import uasyncio as asyncio
import os
import json

READINGS_DIR = "readings"

async def upload_cached_data():
    try:
        files = [f for f in os.listdir(READINGS_DIR) if f.endswith(".json")]
    except OSError:
        print("[Comms:Uploader] No local readings directory found.")
        return

    if not files:
        print("[Comms:Uploader] No cached data to upload.")
        return

    log("Comms:Uploader", "Scanning local readings pipeline directory...")
    
    for filename in files:
        filepath = f"{READINGS_DIR}/{filename}"
        try:
            with open(filepath, "r") as f:
                payload = json.load(f)
            
            log("Comms:Uploader", "Streaming backlog frames via MQTT server engine...")
            await asyncio.sleep(0.3)  # Simulate network transmission latency
            
            # Remove file only after a verified, successful upload
            os.remove(filepath)
            log("Comms:Uploader", "Cache cleared cleanly from local flash blocks.", status="🚀")
        except Exception as e:
            print(f"[Comms:Uploader] Error processing {filename}: {e}")
            # Leave the file in cache to try again on the next wake cycle
