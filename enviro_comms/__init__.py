import uasyncio as asyncio
import event_bus
# FIX: Removed the non-existent '.watchdog' import reference from this package space
from . import wifi, mqtt, ntp, uploader
from logger import log, enable_syslog_upload

class EnviroComms:
    def __init__(self):
        log("Comms:Device", "Enviro Comms Package Instance initialized.", status="⚙️")
        self._sync_requested = False
        self._pipeline_running = False
        event_bus.subscribe("system:gather_data", self._on_gather_data)
        event_bus.subscribe("time:sync_requested", self._on_time_sync_requested)
        event_bus.subscribe("system:run_diagnostics", self._on_run_diagnostics)

    # --- ASYNC BUS EVENT HANDLERS ---
    def _on_time_sync_requested(self):
        self._sync_requested = True

    async def _on_gather_data(self):
        await self.run_pipeline()

    async def _on_run_diagnostics(self):
        from . import network_test
        asyncio.create_task(network_test.verify_network_and_ntp(self))

    async def run_pipeline(self):
        if self._pipeline_running:
            log("Comms:Pipeline", "Pipeline already in progress. Skipping duplicate run.", status="⚠️")
            return False
        self._pipeline_running = True

        try:
            event_bus.publish("comms:started")
            
            if await wifi.connect_async():
                enable_syslog_upload()
                log("Comms:Pipeline", "Physical infrastructure ready. Spawning parallel transport connections...")
                
                event_bus.publish("comms:connected")
                
                tasks = [mqtt.connect_async()]
                if self._sync_requested:
                    tasks.append(ntp.sync_async())
                else:
                    log("Comms:Pipeline", "Hardware clock verified within safe limits. Skipping NTP sync.")
                    
                await asyncio.gather(*tasks)
                self._sync_requested = False
                
                if not mqtt.is_configured():
                    await mqtt.send_config()
                    
                await uploader.upload_cached_data()
                
                event_bus.publish("comms:finished")
                return True
                
            self._sync_requested = False
            event_bus.publish("comms:failed")
            return False
        finally:
            self._pipeline_running = False
