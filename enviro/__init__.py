from machine import Pin
import uasyncio as asyncio
from logger import log
import event_bus  
from . import watchdog, sensors, storage, clock, sleep
from enviro.constants import ACTIVITY_LED_PIN, WARN_LED_BLINK, WARN_LED_OFF, WARN_LED_ON

_network_back_led = Pin("LED", Pin.OUT, value=0)
_green_activity_led = Pin(ACTIVITY_LED_PIN, Pin.OUT, value=0)

class EnviroDevice:
    def __init__(self):
        log("Enviro:Device", "Enviro Device Engine Initialised.", status="⚙️")
        self._register_event_subscriptions()
        
    def _register_event_subscriptions(self):
        event_bus.subscribe("system:check_watchdog_status", self._check_watchdog)
        event_bus.subscribe("system:arm_watchdog", self._on_arm_watchdog)
        event_bus.subscribe("system:gather_data", self._on_gather_data)
        event_bus.subscribe("system:sleep", self._on_sleep)
        event_bus.subscribe("system:run_diagnostics", self._on_run_diagnostics)
        
        event_bus.subscribe("comms:started", self._on_comms_started)
        event_bus.subscribe("comms:connected", self._on_comms_connected)
        event_bus.subscribe("comms:finished", self._on_comms_finished)
        event_bus.subscribe("comms:failed", self._on_comms_failed)
        event_bus.subscribe("time:received", self._on_time_received)

    # --- ASYNC BUS EVENT HANDLERS ---
    async def _check_watchdog(self):
        watchdog.arm()
        watchdog.disarm()

    async def _on_arm_watchdog(self): watchdog.arm()
    async def _on_gather_data(self):
        if not clock.is_clock_set():
            event_bus.publish("time:sync_requested")
        self.capture_and_cache()
        event_bus.publish("storage:cached")
    async def _on_sleep(self): sleep.configure_hardware_sleep()

    async def _on_run_diagnostics(self):
        from . import hardware_test
        import config
        asyncio.create_task(hardware_test.verify_timezone_rules_logic())
        asyncio.create_task(hardware_test.verify_led_concurrency(self))
        if getattr(config, "test_hardware_watchdog_hang", False):
            asyncio.create_task(hardware_test.execute_watchdog_freeze_test(self))

    async def _on_comms_started(self): _network_back_led.value(1)
    async def _on_comms_connected(self):
        self.pulse_green()
        if not clock.is_clock_set():
            event_bus.publish("time:sync_requested")
    async def _on_comms_finished(self): _network_back_led.value(0)
    async def _on_comms_failed(self):
        _network_back_led.value(0)
        clock.set_warn_led(WARN_LED_BLINK)
        
    async def _on_time_received(self, timestamp): clock.commit_ntp_timestamp(timestamp)

    def pulse_green(self):
        _green_activity_led.value(1)
        import time
        time.sleep_ms(60)
        _green_activity_led.value(0)

    def set_network_led(self, state): _network_back_led.value(1 if state else 0)
    def set_warning_led(self, state): clock.set_warn_led(state)

    def capture_and_cache(self):
        self.pulse_green()
        readings = sensors.take_readings()
        storage.save_to_cache(readings)
        return readings
