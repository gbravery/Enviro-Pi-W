from machine import Pin, ADC
import time
import config
from logger import log
from .clock import i2c
from . import helpers

_model = None
_board_module = None
_last_reading_time = None
_vsys_adc = None

def detect_model(i2c_bus=None):
    """
    Identifies the Enviro board model based on I2C devices and pin states:
    - 56 (0x38, BH1745 colour sensor): Indoor
    - 35 (0x23, LTR-559 light sensor):
      - GPIO 12 pulled up: Grow (if low) or Weather (if high)
    - Default: Urban
    """
    global _model
    if hasattr(config, "model") and config.model:
        _model = config.model
        log("Enviro:Sensors", f"Board model manually configured: '{_model}'")
        return _model

    bus = i2c_bus if i2c_bus is not None else i2c
    try:
        i2c_devices = bus.scan()
    except Exception as e:
        log("Enviro:Sensors", f"I2C bus scan failed during board identification: {e}", status="⚠️")
        i2c_devices = []

    if 56 in i2c_devices:
        _model = "indoor"
    elif 35 in i2c_devices:
        try:
            pump3_pin = Pin(12, Pin.IN, Pin.PULL_UP)
            _model = "grow" if pump3_pin.value() == 0 else "weather"
            pump3_pin.init(pull=None)
        except Exception:
            _model = "weather"
    else:
        _model = "urban"

    log("Enviro:Sensors", f"Identified hardware board model: '{_model}' (I2C: {i2c_devices})")
    return _model

def get_model():
    """Returns the cached board model name, detecting it if not yet identified."""
    global _model
    if _model is None:
        _model = detect_model()
    return _model

def get_board(model_name=None):
    """Dynamically imports and returns the driver module for the specified or detected board model."""
    global _board_module
    if model_name is None:
        model_name = get_model()

    if _board_module is None:
        if model_name == "indoor":
            from .boards import indoor as board
        elif model_name == "grow":
            from .boards import grow as board
        elif model_name == "weather":
            from .boards import weather as board
        elif model_name == "urban":
            from .boards import urban as board
        else:
            raise ValueError(f"Unknown board model: '{model_name}'")
        _board_module = board

    return _board_module

def get_battery_voltage():
    """Reads the VSYS battery voltage via ADC(29) with 1:3 resistor divider compensation."""
    global _vsys_adc
    try:
        if _vsys_adc is None:
            _vsys_adc = ADC(29)
        raw = _vsys_adc.read_u16()
        voltage = (raw * 3.3 / 65535.0) * 3.0
        return round(voltage, 2)
    except Exception as e:
        log("Enviro:Sensors", f"Failed to read battery voltage: {e}", status="⚠️")
        return None

def take_readings():
    """Queries the active board module for real sensor telemetry and formats the payload."""
    global _last_reading_time
    model_name = get_model()
    board = get_board(model_name)

    now = time.time()
    seconds_since_last = 0
    if _last_reading_time is not None and now >= _last_reading_time:
        seconds_since_last = now - _last_reading_time
    _last_reading_time = now

    is_usb_power = getattr(config, "vbus_present", True)
    
    log("Enviro:Sensors", f"Reading sensors via '{model_name}' board driver...")
    try:
        sensor_data = board.get_sensor_readings(seconds_since_last, is_usb_power)
    except Exception as e:
        log("Enviro:Sensors", f"Error reading board sensors: {e}", status="⚠️")
        sensor_data = {}

    readings = dict(sensor_data) if hasattr(sensor_data, "items") else {}

    if getattr(config, "enable_battery_voltage", True):
        voltage = get_battery_voltage()
        if voltage is not None:
            readings["voltage"] = voltage

    payload = {
        "nickname": getattr(config, "nickname", "enviropi"),
        "timestamp": helpers.datetime_string(),
        "readings": readings,
        "model": model_name,
        "uid": helpers.uid()
    }
    log("Enviro:Sensors", f"Telemetry captured successfully ({len(readings)} metrics).", status="✅")
    return payload

def sleep():
    """Calls board-specific sleep routines if supported."""
    try:
        board = get_board()
        if hasattr(board, "sleep"):
            board.sleep()
    except Exception as e:
        log("Enviro:Sensors", f"Board sleep routine skipped: {e}", status="⚠️")
