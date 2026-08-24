from enviro.constants import (
    WATER_VAPOR_SPECIFIC_GAS_CONSTANT,
    CRITICAL_WATER_TEMPERATURE,
    CRITICAL_WATER_PRESSURE
)
import machine
import math
import os
import time

def datetime_string():
    dt = machine.RTC().datetime()
    return "{0:04d}-{1:02d}-{2:02d}T{4:02d}:{5:02d}:{6:02d}Z".format(*dt)

def datetime_file_string():
    dt = machine.RTC().datetime()
    return "{0:04d}-{1:02d}-{2:02d}T{4:02d}_{5:02d}_{6:02d}Z".format(*dt)

def date_string():
    dt = machine.RTC().datetime()
    return "{0:04d}-{1:02d}-{2:02d}".format(*dt)

def timestamp(dt):
    year = int(dt[0:4])
    month = int(dt[5:7])
    day = int(dt[8:10])
    hour = int(dt[11:13])
    minute = int(dt[14:16])
    second = int(dt[17:19])
    return time.mktime((year, month, day, hour, minute, second, 0, 0))

def timestamp_day(dt, offset_hours=0):
    t = timestamp(dt)
    t = t + (offset_hours * 3600)
    lt = time.localtime(t)
    return int(lt[2])

def uid():
    return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(*machine.unique_id())

def file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def celcius_to_kelvin(temperature_in_c):
    return temperature_in_c + 273.15

def get_actual_vapor_pressure(relative_humidity, temperature_in_k):
    return get_saturation_vapor_pressure(temperature_in_k) * (relative_humidity / 100)

def get_saturation_vapor_pressure(temperature_in_k):
    v = 1 - (temperature_in_k / CRITICAL_WATER_TEMPERATURE)
    a1 = -7.85951783
    a2 = 1.84408259
    a3 = -11.7866497
    a4 = 22.6807411
    a5 = -15.9618719
    a6 = 1.80122502

    return CRITICAL_WATER_PRESSURE * math.exp(
        CRITICAL_WATER_TEMPERATURE /
        temperature_in_k *
        (a1*v + a2*v**1.5 + a3*v**3 + a4*v**3.5 + a5*v**4 + a6*v**7.5)
    )

def relative_to_absolute_humidity(relative_humidity, temperature_in_c):
    temperature_in_k = celcius_to_kelvin(temperature_in_c)
    actual_vapor_pressure = get_actual_vapor_pressure(relative_humidity, temperature_in_k)
    return actual_vapor_pressure / (WATER_VAPOR_SPECIFIC_GAS_CONSTANT * temperature_in_k)

def absolute_to_relative_humidity(absolute_humidity, temperature_in_c):
    temperature_in_k = celcius_to_kelvin(temperature_in_c)
    saturation_vapor_pressure = get_saturation_vapor_pressure(temperature_in_k)
    return (WATER_VAPOR_SPECIFIC_GAS_CONSTANT * temperature_in_k * absolute_humidity) / saturation_vapor_pressure * 100
