import time
from machine import RTC
import config

# Logging severity constants matching usyslog definitions
S_WARN = 4
S_INFO = 6

_log_cache = []
_syslog_client = None
_network_ready = False

# Read device identification nickname from config
DEVICE_NICKNAME = getattr(config, "nickname", "enviro-device")

# Cached timezone bounds (calculated dynamically in memory)
_cached_year = None
_bst_start_epoch = 0
_bst_end_epoch = 0
_current_offset_hours = 0

def _calculate_last_sunday(year, month):
    """Finds the day-of-the-month number for the last Sunday of a specific month."""
    # Start at the absolute last day of the month (March 31st or October 31st)
    for day in range(31, 23, -1):
        # time.mktime expects: (year, month, day, hour, minute, second, weekday, yearday)
        t_struct = time.mktime((year, month, day, 1, 0, 0, 0, 0))
        # time.localtime(t_struct)[6] returns the weekday integer (0 = Monday, 6 = Sunday)
        if time.localtime(t_struct)[6] == 6:
            return day
    return 31

def update_timezone_cache(year):
    """
    Computes the exact Unix Epoch seconds for the seasonal transitions of the current year.
    Caches the results globally to optimize runtime log performance.
    """
    global _cached_year, _bst_start_epoch, _bst_end_epoch
    
    # 1. Calculate transition days (Last Sunday of March and October)
    march_sunday = _calculate_last_sunday(year, 3)
    october_sunday = _calculate_last_sunday(year, 10)
    
    # 2. Convert transitions to exact UTC Unix timestamps
    # BST starts at 01:00 UTC on the last Sunday of March
    _bst_start_epoch = time.mktime((year, 3, march_sunday, 1, 0, 0, 0, 0))
    # BST ends at 01:00 UTC (02:00 BST) on the last Sunday of October
    _bst_end_epoch = time.mktime((year, 10, october_sunday, 1, 0, 0, 0, 0))
    
    _cached_year = year

def get_current_timezone_offset(utc_secs):
    """
    Compares the current live UTC timestamp against cached seasonal bounds
    to determine if the system is actively in British Summer Time (BST).
    """
    global _cached_year, _current_offset_hours
    
    # Check current calendar layout
    current_year = time.localtime(utc_secs)[0]
    
    # Recompute the transition boundaries only if the year has changed
    if current_year != _cached_year:
        update_timezone_cache(current_year)
        
    # If our live timestamp falls between the transition markers, apply BST (+1)
    if _bst_start_epoch <= utc_secs < _bst_end_epoch:
        _current_offset_hours = 1
    else:
        _current_offset_hours = 0
        
    return _current_offset_hours

def calculate_local_iso_string():
    """
    Reads pure UTC from hardware, evaluates the dynamic rule cache,
    and returns a structured high-precision ISO-8601 string.
    """
    # 1. Grab pure hardware UTC
    dt = RTC().datetime()
    us = time.ticks_us() % 1000000
    
    # 2. Convert current time components to absolute Unix seconds
    utc_secs = time.mktime((dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], 0, 0))
    
    # 3. Dynamically evaluate current offset status
    offset = get_current_timezone_offset(utc_secs)
    
    # 4. If offset is active, shift timestamps smoothly
    if offset != 0:
        local_dt = time.localtime(utc_secs + (offset * 3600))
        year, month, day, hour, minute, second = local_dt[0:6]
        tz_string = f"+{offset:02d}:00"
    else:
        year, month, day, hour, minute, second = dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
        tz_string = "Z"  # Zulu indicator for true UTC
        
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}.{us:06d}{tz_string}"

def log(tag, message, status=None, severity=S_INFO):
    """Unified high-precision logger with dynamic timezone rules handling."""
    global _network_ready, _syslog_client
    
    timestamp = calculate_local_iso_string()
    bracket_tag = f"[{tag}]"
    formatted_tag = f"{bracket_tag:<22}"
    status_icon = f" {status}" if status else ""
    
    # Local terminal screen print string layout
    screen_log_line = f"{timestamp} {formatted_tag} {message}{status_icon}"
    print(screen_log_line)
    
    # Pack standard RFC 5424 structured payload
    rfc5424_msg = f"1 {timestamp} {DEVICE_NICKNAME} enviro - - - {bracket_tag} {message}{status_icon}"
    
    if not _network_ready:
        _log_cache.append((severity, rfc5424_msg))
    else:
        try:
            _syslog_client.log(severity, rfc5424_msg)
        except OSError:
            pass

def enable_syslog_upload():
    """Initialises usyslog and drains the cached boot frames."""
    global _network_ready, _syslog_client
    from enviro_comms.usyslog import UDPClient, F_USER
    
    host = getattr(config, "syslog_server", "192.168.1.100")
    port = getattr(config, "syslog_port", 514)
    
    log("Main:Logger", f"Connecting usyslog client to server reference [{host}:{port}]...")
    
    try:
        _syslog_client = UDPClient(ip=host, port=port, facility=F_USER)
        _network_ready = True
        
        if _log_cache:
            log("Main:Logger", f"Network live. Flushing {len(_log_cache)} cached boot records to server...")
            while _log_cache:
                severity, complete_rfc_frame = _log_cache.pop(0)
                _syslog_client.log(severity, complete_rfc_frame)
            log("Main:Logger", "Early boot diagnostic cache successfully drained.", status="🚀")
    except Exception as e:
        _network_ready = False
        log("Main:Logger", f"Failed to instantiate usyslog socket engine: {e}", status="❌")
