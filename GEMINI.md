# Technical Project Specification: 
Decoupled Async Core ChassisTarget Environment: 
MicroPython 1.23+ (Raspberry Pi Pico W / RP2040)Hardware Appliance Context: Pimoroni Enviro Pi Garden (PCF85063A External I2C RTC, Shared I2C IO Expanders, CYW43 Wi-Fi Core)

## 1. Architectural Philosophy & Directory Structure
The application enforces strict domain separation. The core orchestrator (main.py) does not possess direct cross-imports to localized functional submodules. Communication across package boundaries is handled completely through an asynchronous mediator pattern (Message Broker Event Bus).
├── enviro/                 # Physical Hardware Domain Package
│   ├── __init__.py         # Hardware Wrapper & Event Bus Subscription Bindings
│   ├── constants.py        # Static GPIO, Register Addresses, & State Keys
│   ├── clock.py            # I2C Bus Management & PCF85063A Hardware Registers
│   ├── sleep.py            # Hardware Alarm Configuration & Battery/USB Power Routing
│   ├── sensors.py          # Real Telemetry Sample Collection Pipeline
│   └── storage.py          # Atomic Non-blocking Local Flash Persistence Queue
├── enviro_comms/           # Network Infrastructure Domain Package
│   ├── __init__.py         # Comms Wrapper & Event Bus Pipeline Trigger Orchestration
│   ├── wifi.py             # Async CYW43 Physical Layer Initialization Loops
│   ├── ntp.py              # UDP Network Time Protocol (NTP) Client Socket Engine
│   └── usyslog.py          # RFC-5424 Raw Diagnostic Syslog UDP Transmitter
├── logger.py               # Root Namespace System High-Precision ISO-8601 Engine
├── event_bus.py            # Root Namespace Micro-Task Callback Event Broker Broker
└── main.py                 # Structural Application Appliance Loop Chassis

## 2. Core Subsystem Implementations
### A. Event Bus Engine (event_bus.py)
A lightweight publish-subscribe model designed to prevent race conditions on MicroPython’s single-threaded async event loop. It automatically detects if a registered callback function is synchronous or an asynchronous generator/coroutine, wrapping the execution safely inside an isolated background micro-task wrapper via asyncio.create_task().
### B. High-Precision Syslog Logger (logger.py)
Timestamp Precision: Generates strict ISO-8601 formatting down to the microsecond level (YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM) by combining machine.RTC().datetime() records with high-speed ticker offsets derived from time.ticks_us() % 1000000.
Dynamic Timezone Rules Engine: Computes exact Unix Epoch markers in memory once on boot or NTP sync for seasonal transitions (e.g., British Summer Time rules: Last Sunday of March to Last Sunday of October). Employs ultra-fast numerical evaluation range comparisons (start_epoch <= current_epoch < end_epoch) to bypass cycle-intensive text parsing on log triggers.
Early Boot Caching & Live Offloading: Caches early-boot diagnostic traces in memory as (severity, message) tuples while the network link is offline. Once the communication pipeline is online, it dynamically initializes the usyslog.UDPClient on Port 514, formats clean RFC-5424 packages, flushes the cached block sequentially using .pop(0) memory clear loops to prevent heap congestion, and shifts subsequential logs to stream live.
### C. Time, Alarm, & Power Management Logic (enviro/sleep.py)
**Hardware RTC Reference Strategy: **The physical off-chip PCF85063A real-time clock chip runs permanently on unshifted Coordinated Universal Time (UTC).PAYLOAD data maps are saved and published upstream in pure UTC. Timezone adjustments are performed on-the-fly dynamically solely inside display/syslog string formatting loops.Interval Calculations: Truncates trailing execution runtime seconds drift completely to zero. Calculates next target intervals securely using loopless, non-branching modular arithmetic and integer division:
python
`total_minutes = current_minute + int(interval_minutes)
target_minute = total_minutes % 60
target_hour = (current_hour + (total_minutes // 60)) % 24
`
**Hardware Interface Constraints: **
Interacts with the Pimoroni library wrapper signature explicitly formatted by raw positional arguments rtc_chip.set_alarm(hour, minute) to prevent MicroPython C-library keyword mapping errors.

**Hybrid Power Routing Configuration:**
Battery Power Path: Cleans the filesystem hang-check file tracker, arms the low-level PIO state-machine hardware crash watchdog, configures the PCF85063A interrupt match register, and forces a complete physical hardware shutdown by dragging the HOLD_VSYS_EN_PIN actively to 0V in an infinite while loop to counteract residual capacitor voltage leaks. The board draws zero current until the hardware alarm fires to toggle the power regulator line back ON.
USB Power Path (Thonny Safe Debug): Throws a custom runtime error token intercepted natively by main.py. This drops the microcontroller into an unblocked, non-destructive virtual sleep state utilizing asyncio.wait_for(). Computes precise alignment sleep durations down to the top of the next minute boundary via:
total_sleep_seconds = int(interval) * 60 - current_seconds
This maintains active Thonny serial USB communication channels open continuously for desktop debugging across cycles.

## 3. The Structural Loop Chassis (main.py)
Operates as a pure event-driven shell orchestrator with zero direct dependencies or class reference requirements pointing to sub-modules. It listens for token string alerts published to the broker network (storage:cached, comms:finished, system:wake) and coordinates operations using atomic asyncio.Event() locks.
Includes an active background USB Serial Input Scanner Task that samples sys.stdin using non-blocking select.select() queries at 10Hz. Tapping the character w forces a safe virtual wakeup loop bypass, and tapping the character q invokes a clean application shutdown sequence that drops hardware indicators safely and tears down the active async task loops before terminating the application.

## 4. Active Target Status
All baseline hardware indicators, timezone modules, cross-reboot PIO watchdogs, file management layers, dynamic power-routing systems, and concurrent event bus channels are locked down, optimized, and performing stably on the device.
The structure is prepared to deploy the real asynchronous MQTT transmitter engine inside enviro_comms/mqtt.py or compile the physical hardware register scanning variables into enviro/sensors.py.

## 5. Diagnostic & Test Chassis Standards
- **Mandatory Test Updates**: Every architectural, hardware, comms, or file system change must be paired with corresponding automated diagnostic verification routines added to the appropriate test chassis:
  - `enviro/hardware_test.py` for physical RTC, pinouts, GPIO, LEDs, watchdog, flash marker tracking, and timezone rules.
  - `enviro_comms/network_test.py` for CYW43 Wi-Fi physical links, socket UDP NTP client handshakes, MQTT broker sessions, and data streaming uploaders.
- **MicroPython Safe Execution**: Tests must handle missing files, backup real runtime states before running, restore original state upon test conclusion, and output formatted status tokens via `logger.log` (e.g. `status="✅"` or `status="❌"`).