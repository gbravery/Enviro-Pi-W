import time
from logger import log

def take_readings():
    log("Enviro:Sensors", "Reading hardware registers...")
    time.sleep(0.1)
    
    payload = {
        "timestamp": time.time(),
        "temperature": 24.1,
        "humidity": 42.8
    }
    log("Enviro:Sensors", "Telemetry captured.", status="✅")
    return payload

def sleep():
    log("Enviro:Sensors", "Cutting hardware rails. Entering deep sleep...", status="💤")
