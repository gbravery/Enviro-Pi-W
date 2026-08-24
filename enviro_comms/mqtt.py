import uasyncio as asyncio
import config
from logger import log

# Change from 'def' to 'async def' so it returns a valid coroutine object
async def connect_async():
    broker = getattr(config, "mqtt_broker", "localhost")
    log("Comms:MQTT", f"Opening transport layer stream to host: {broker}...")
    await asyncio.sleep(0.6)  # Simulated connection delay
    log("Comms:MQTT", "Broker context initialized.", status="✅")

def is_configured():
    return getattr(config, "mqtt_configured", False)

# Change from 'def' to 'async def' for future safety since it uses sleep
async def send_config():
    log("Comms:MQTT", "Publishing home assistant autodiscovery payload...")
    await asyncio.sleep(0.3)
    log("Comms:MQTT", "Definitions sent.", status="✅")
