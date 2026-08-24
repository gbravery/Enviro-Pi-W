import time
import uasyncio as asyncio
import config
import event_bus
import sys
import select
from logger import log

# Pipeline state tracking flags
_sensor_cycle_complete = False
_network_cycle_complete = False
_iteration_done_event = asyncio.Event()
_wake_event = asyncio.Event()
_shutdown_loop_flag = False

def on_storage_cached():
    global _sensor_cycle_complete
    _sensor_cycle_complete = True
    _check_iteration_status()

def on_pipeline_finished():
    global _network_cycle_complete
    _network_cycle_complete = True
    _check_iteration_status()

def on_poke_interrupt():
    """Fires instantly if the user presses the physical POKE button during virtual sleep."""
    log("Chassis:Engine", "POKE button event caught! Forcing early software wakeup loop...", status="⚡")
    _wake_event.set()

def _check_iteration_status():
    if _sensor_cycle_complete and _network_cycle_complete:
        _iteration_done_event.set()

def register_chassis_subscriptions():
    event_bus.subscribe("storage:cached", on_storage_cached)
    event_bus.subscribe("comms:finished", on_pipeline_finished)
    event_bus.subscribe("comms:failed", on_pipeline_finished)
    event_bus.subscribe("system:poke", on_poke_interrupt)

async def monitor_keyboard_input_loop():
    """
    Non-blocking background loop that scans the USB serial line for debug commands.
    Runs smoothly alongside other tasks without starving the CPU scheduler.
    """
    global _shutdown_loop_flag
    while True:
        # Check if characters are waiting in the stdin buffer
        if select.select([sys.stdin], [], [], 0)[0]:
            # Consume and clear the keystroke cleanly from memory
            char = sys.stdin.read(1).lower()
            
            if char == 'w':
                log("Chassis:Input", "Keyboard command 'w' intercepted! Forcing virtual wake...", status="⚡")
                _wake_event.set()
            elif char == 'q':
                log("Chassis:Input", "Keyboard command 'q' intercepted! Initiating clean shutdown...", status="🛑")
                _shutdown_loop_flag = True
                _wake_event.set() # Instantly unblocks the sleep wait state
                
        # Poll the terminal buffer 10 times a second to keep it responsive
        await asyncio.sleep(0.1)

async def run_production_iteration():
    global _sensor_cycle_complete, _network_cycle_complete
    _sensor_cycle_complete = False
    _network_cycle_complete = False
    _iteration_done_event.clear()

    log("Chassis:Engine", "--- Initiating Production Parallel Loop Engine ---")
    event_bus.publish("system:arm_watchdog")
    event_bus.publish("system:gather_data")
    
    await _iteration_done_event.wait()
    log("Chassis:Engine", "--- Cycle Successfully Concluded ---")
    event_bus.publish("system:sleep")

async def execute_usb_chassis_sleep():
    """Handles the virtual low-power countdown duration securely inside the main thread context."""
    from enviro.clock import set_warn_led
    from enviro.constants import WARN_LED_BLINK, WARN_LED_OFF
    
    interval = getattr(config, "reading_frequency", 15)
    log("Chassis:Sleep", f"Entering virtual sleep state. Aligning to next {interval} minute boundary (00s)...")
    log("Chassis:Sleep", "💬 [Thonpi Debug] Press 'w' to Wake Instantly | Press 'q' to Shutdown cleanly.")
    set_warn_led(WARN_LED_BLINK)
    
    # Calculate exactly how many seconds are left until the top of the target minute
    current_seconds = time.localtime()[5]
    total_sleep_seconds = int(interval) * 60 - current_seconds
    
    # Use a non-blocking timeout check to wait cleanly until the time clears or POKE is pressed
    try:
        await asyncio.wait_for(_wake_event.wait(), total_sleep_seconds)
    except asyncio.TimeoutError:
        log("Chassis:Sleep", "⏰ WAKEUP TIMEOUT REACHED! Resuming application loop context...", status="⚡")
        
    set_warn_led(WARN_LED_OFF)
    _wake_event.clear()

async def main_chassis_coordinator():
    if hasattr(event_bus, "clear"):
        event_bus.clear()
    elif hasattr(event_bus, "_subscribers"):
        event_bus._subscribers.clear()
    register_chassis_subscriptions()
    
    from enviro import EnviroDevice
    from enviro_comms import EnviroComms
    _ = EnviroDevice()
    _ = EnviroComms()
    
    event_bus.publish("system:check_watchdog_status")
    
    if getattr(config, "execute_system_tests", False):
        log("Chassis:Test", "Executing active testing chassis routing parameter...")
        event_bus.publish("system:run_diagnostics")
        await asyncio.sleep(6.0)
    else:
        # Spin up our dedicated asynchronous keyboard scanner task right here
        asyncio.create_task(monitor_keyboard_input_loop())
 
        # Persistent event listener to orchestrate the sleep cycles smoothly
        sleep_active_event = asyncio.Event()
        event_bus.subscribe("system:sleep_active", lambda: sleep_active_event.set())
        
        while True:
            await run_production_iteration()
            
            if getattr(config, "vbus_present", True):
                # Wait until the hardware package finishes setting its alarm registers
                await sleep_active_event.wait()
                sleep_active_event.clear()
                
                # Run the stable, unblocked virtual countdown
                await execute_usb_chassis_sleep()
                # Check if a shutdown command was processed during the sleep state
                if _shutdown_loop_flag:
                    log("Chassis:Engine", "Terminating execution chassis framework cleanly. Goodbye!", status="🛑")
                    break
            else:
                # If running on batteries, the hardware line shuts off during run_production_iteration
                break

        # Clean wind-down: clear active indicators before stopping the interpreter
        from enviro.clock import set_warn_led
        from enviro.constants import WARN_LED_OFF
        set_warn_led(WARN_LED_OFF)
        asyncio.get_event_loop().stop()

asyncio.run(main_chassis_coordinator())
