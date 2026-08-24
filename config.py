# enviro config file

# you may edit this file by hand but if you enter provisioning mode
# then the file will be automatically overwritten with new details

provisioned = True

# enter a nickname for this board
nickname = 'enviropi-oldgarden'

# network access details
wifi_ssid = 'JagsiacsMesh'
wifi_password = 'TheDeathlyHallows:Part2'
wifi_country = "GB"

ntp_server="192.168.1.254"
syslog_server="192.168.1.2"

# Adjust daily rain day for UK BST
uk_bst = True

# For local time corrections to daily rain logging other than BST
# Ignored if uk_bst = True
utc_offset = 0

# how often to wake up and take a reading (in minutes)
#reading_frequency = 5
reading_frequency = 2

# how often to trigger a resync of the onboard RTC (in hours)
resync_frequency = 168

# where to upload to ("http", "mqtt", "adafruit_io", "influxdb")
destination = 'influxdb'

# how often to upload data (number of cached readings)
upload_frequency = 3

# Feature toggles
enable_battery_voltage = True

# Watchdog timer in whole minutes (integer), 0 is not active 
#pio_watchdog_time = 10
pio_watchdog_time = 1

# web hook settings
custom_http_url = None
custom_http_username = None
custom_http_password = None

# mqtt broker settings
mqtt_broker_address = None
mqtt_broker_username = None
mqtt_broker_password = None
# mqtt broker if using local SSL
mqtt_broker_ca_file = None

# adafruit ui settings
adafruit_io_username = None
adafruit_io_key = None

# influxdb settings
influxdb_org = 'jagsiacs'
influxdb_url = 'http://nas:48086'
influxdb_token = 'my-super-secret-auth-token'
influxdb_bucket = 'household'

# grow specific settings
auto_water = False
moisture_target_a = 50
moisture_target_b = 50
moisture_target_c = 50

# compensate for usb power - degrees to remove from measured temperature
usb_power_temperature_offset = 4.5

# offset up to +/- 360 degrees for wind direction if you can't reorientate the weather station
wind_direction_offset = 0

# --- THE CHASSIS EXECUTION MANAGER SWITCHES ---
execute_system_tests          = False   # Set to False to run production loops normally
test_hardware_timezone        = True   # Test your local GMT/BST calculation strings
test_hardware_leds            = True   # Flash the red/green/back LEDs for 5 seconds
test_infrastructure_network   = True   # Connect to real Wi-Fi and fetch real NTP values
test_hardware_watchdog_hang   = True  # Set to True to intentionally crash the board

