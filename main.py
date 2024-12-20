import time
import network
import urequests
import ujson
from machine import UART, Pin
import ubinascii
from wifi_manager import connect_to_saved_wifi, start_access_point, start_web_server

# Server endpoint
SERVER_URL = 'https://maroon-aardvark-466472.hostingersite.com/save_location.php'

# Initialize UART for GPS communication
gps_uart = UART(2, baudrate=9600, tx=18, rx=19)  # Adjust pins according to your setup

# Initialize SOS Buttons and LED
sos_button = Pin(23, Pin.IN, Pin.PULL_UP)  # SOS button on GPIO22
sos_off_button = Pin(21, Pin.IN, Pin.PULL_UP)  # SOS OFF button on GPIO21
sos_led = Pin(22, Pin.OUT)  # LED on GPIO23 for SOS status
sos_led.value(0)  # Ensure LED is turned off on startup
sos_triggered = False  # Track if SOS is active

# Debouncing variables
last_sos_press_time = 0
last_sos_off_press_time = 0
debounce_delay = 300  # in milliseconds

# Location update interval
last_location_update_time = 0
location_update_interval = 5000  # in milliseconds (5 seconds)

# Retrieve MAC address
def get_mac_address():
    mac_address = ubinascii.hexlify(network.WLAN(network.STA_IF).config('mac'), ':').decode()
    print(f"[{time.localtime()}] ESP32 MAC Address: {mac_address}")
    return mac_address

# Read GPS data
def get_gps_data():
    buffer = ""
    while gps_uart.any():
        try:
            data = gps_uart.read()
            if data:
                buffer += data.decode('utf-8')
        except UnicodeError:
            print(f"[{time.localtime()}] Unicode error in GPS data. Skipping invalid characters.")
            continue

    for line in buffer.splitlines():
        if line.startswith('$GPGGA'):
            print(f"[{time.localtime()}] Raw GPGGA line: {line}")
            parts = line.split(',')
            if len(parts) > 9 and parts[2] and parts[4]:
                try:
                    fix_quality = parts[6]
                    if fix_quality in ['1', '2']:
                        latitude = convert_to_decimal(parts[2], parts[3], is_latitude=True)
                        longitude = convert_to_decimal(parts[4], parts[5], is_latitude=False)
                        return latitude, longitude
                except ValueError:
                    print("Invalid coordinate format.")
    return None, None

# Convert GPS NMEA format to decimal degrees
def convert_to_decimal(coord, direction, is_latitude):
    try:
        degrees = float(coord[:2]) if is_latitude else float(coord[:3])
        minutes = float(coord[2:]) if is_latitude else float(coord[3:])
        decimal = degrees + (minutes / 60)
        if direction == 'S' or direction == 'W':
            decimal = -decimal
        print(f"Converting coord: {coord}, Direction: {direction} -> {decimal}")
        return decimal
    except ValueError:
        print("Invalid coordinate format in conversion.")
        return None

# Send data to server
def send_data(latitude, longitude, mac_address, sos_status):
    payload = {
        "latitude": latitude,
        "longitude": longitude,
        "mac_address": mac_address,
        "sos": sos_status  # Include SOS status in the payload
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = urequests.post(SERVER_URL, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'})
            if response.status_code == 200:
                print(f"[{time.localtime()}] Data successfully sent! Response: {response.text}")
                response.close()
                break
            else:
                print(f"[{time.localtime()}] Failed to send data. Server responded with: {response.status_code}")
        except Exception as e:
            print(f"[{time.localtime()}] Attempt {attempt + 1} failed: {e}")
            time.sleep(2)  # Wait before retrying

# Main code
if not connect_to_saved_wifi():  # Attempt to connect to saved WiFi
    start_access_point()         # Start AP mode if WiFi connection fails
    start_web_server()           # Start configuration portal

mac_address = get_mac_address()

# Main loop
while True:
    current_time = time.ticks_ms()

    # Periodic location updates every 5 seconds
    if time.ticks_diff(current_time, last_location_update_time) > location_update_interval:
        last_location_update_time = current_time
        latitude, longitude = get_gps_data()
        if latitude is not None and longitude is not None:
            print("Periodic location update.")
            send_data(latitude, longitude, mac_address, sos_triggered)
        else:
            print("No valid GPS fix. Skipping data send.")

    # Check SOS button state with debouncing
    if not sos_button.value() and time.ticks_diff(current_time, last_sos_press_time) > debounce_delay:
        last_sos_press_time = current_time
        if not sos_triggered:  # Trigger SOS only if not already active
            sos_triggered = True
            sos_led.value(1)  # Turn on SOS LED
            print("SOS triggered!")
            latitude, longitude = get_gps_data()
            if latitude is not None and longitude is not None:
                send_data(latitude, longitude, mac_address, sos_triggered)
            else:
                print("No valid GPS fix during SOS. Skipping data send.")

    # Check SOS OFF button state with debouncing
    if not sos_off_button.value() and time.ticks_diff(current_time, last_sos_off_press_time) > debounce_delay:
        last_sos_off_press_time = current_time
        if sos_triggered:  # Turn off SOS only if it is active
            sos_triggered = False
            sos_led.value(0)  # Turn off SOS LED
            print("SOS turned off.")
            latitude, longitude = get_gps_data()
            if latitude is not None and longitude is not None:
                send_data(latitude, longitude, mac_address, sos_triggered)
            else:
                print("No valid GPS fix during SOS OFF. Skipping data send.")

    time.sleep(0.1)  # Poll buttons every 100ms




# import time
# import network
# import urequests
# import ujson
# from machine import UART, Pin
# import ubinascii
# from wifi_manager import connect_to_saved_wifi, start_access_point, start_web_server

# # Server endpoint
# SERVER_URL = 'https://maroon-aardvark-466472.hostingersite.com/save_location.php'

# # Initialize UART for GPS communication
# gps_uart = UART(2, baudrate=9600, tx=19, rx=18)  # Adjust pins according to your setup

# # Initialize SOS Buttons and LED
# sos_button = Pin(23, Pin.IN, Pin.PULL_UP)  # SOS button on GPIO22
# sos_off_button = Pin(21, Pin.IN, Pin.PULL_UP)  # SOS OFF button on GPIO21
# sos_led = Pin(22, Pin.OUT)  # LED on GPIO23 for SOS status
# sos_led.value(0)  # Ensure LED is turned off on startup
# sos_triggered = False  # Track if SOS is active

# # Debouncing variables
# last_sos_press_time = 0
# last_sos_off_press_time = 0
# debounce_delay = 300  # in milliseconds

# # Location update interval
# last_location_update_time = 0
# location_update_interval = 5000  # in milliseconds (5 seconds)

# # Retrieve MAC address
# def get_mac_address():
#     mac_address = ubinascii.hexlify(network.WLAN(network.STA_IF).config('mac'), ':').decode()
#     print(f"[{time.localtime()}] ESP32 MAC Address: {mac_address}")
#     return mac_address

# # Read GPS data
# def get_gps_data():
#     buffer = ""
#     while gps_uart.any():
#         try:
#             data = gps_uart.read()
#             if data:
#                 buffer += data.decode('utf-8')
#         except UnicodeError:
#             print("Unicode error in GPS data. Skipping invalid characters.")
#             continue
#         except Exception as e:
#             print("Error reading GPS data:", e)
#             return None, None

#     for line in buffer.splitlines():
#         if line.startswith('$GPGGA'):
#             parts = line.split(',')
#             print("GPS Parts:", parts)

#             if len(parts) > 9 and parts[2] and parts[4]:
#                 try:
#                     fix_quality = parts[6]
#                     if fix_quality in ['1', '2']:
#                         latitude = convert_to_decimal(parts[2], parts[3], is_latitude=True)
#                         longitude = convert_to_decimal(parts[4], parts[5], is_latitude=False)
#                         print(f"[{time.localtime()}] Latitude: {latitude}, Longitude: {longitude}")
#                         return latitude, longitude
#                     else:
#                         print(f"Fix quality is invalid: {fix_quality}")
#                 except ValueError:
#                     print("Invalid coordinate format.")
#             else:
#                 print("Incomplete or invalid GPGGA sentence.")
#     return None, None

# # Convert GPS NMEA format to decimal degrees
# def convert_to_decimal(coord, direction, is_latitude):
#     try:
#         degrees = float(coord[:2]) if is_latitude else float(coord[:3])
#         minutes = float(coord[2:]) if is_latitude else float(coord[3:])
#         decimal = degrees + (minutes / 60)
#         if direction == 'S' or direction == 'W':
#             decimal = -decimal
#         print(f"Converting coord: {coord}, Direction: {direction} -> {decimal}")
#         return decimal
#     except ValueError:
#         print("Invalid coordinate format in conversion.")
#         return None

# # Send data to server
# def send_data(latitude, longitude, mac_address, sos_status):
#     payload = {
#         "latitude": latitude,
#         "longitude": longitude,
#         "mac_address": mac_address,
#         "sos": sos_status  # Include SOS status in the payload
#     }
#     max_retries = 3
#     for attempt in range(max_retries):
#         try:
#             response = urequests.post(SERVER_URL, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'})
#             if response.status_code == 200:
#                 print(f"[{time.localtime()}] Data successfully sent! Response: {response.text}")
#                 response.close()
#                 break
#             else:
#                 print(f"[{time.localtime()}] Failed to send data. Server responded with: {response.status_code}")
#         except Exception as e:
#             print(f"[{time.localtime()}] Attempt {attempt + 1} failed: {e}")
#             time.sleep(2)  # Wait before retrying

# # Main code
# if not connect_to_saved_wifi():  # Attempt to connect to saved WiFi
#     start_access_point()         # Start AP mode if WiFi connection fails
#     start_web_server()           # Start configuration portal

# mac_address = get_mac_address()

# # Main loop
# while True:
#     current_time = time.ticks_ms()

#     # Periodic location updates every 5 seconds
#     if time.ticks_diff(current_time, last_location_update_time) > location_update_interval:
#         last_location_update_time = current_time
#         latitude, longitude = get_gps_data()
#         if latitude is not None and longitude is not None:
#             print("Periodic location update.")
#             send_data(latitude, longitude, mac_address, sos_triggered)

#     # Check SOS button state with debouncing
#     if not sos_button.value() and time.ticks_diff(current_time, last_sos_press_time) > debounce_delay:
#         last_sos_press_time = current_time
#         if not sos_triggered:  # Trigger SOS only if not already active
#             sos_triggered = True
#             sos_led.value(1)  # Turn on SOS LED
#             print("SOS triggered!")
#             latitude, longitude = get_gps_data()
#             if latitude is not None and longitude is not None:
#                 send_data(latitude, longitude, mac_address, sos_triggered)

#     # Check SOS OFF button state with debouncing
#     if not sos_off_button.value() and time.ticks_diff(current_time, last_sos_off_press_time) > debounce_delay:
#         last_sos_off_press_time = current_time
#         if sos_triggered:  # Turn off SOS only if it is active
#             sos_triggered = False
#             sos_led.value(0)  # Turn off SOS LED
#             print("SOS turned off.")
#             latitude, longitude = get_gps_data()
#             if latitude is not None and longitude is not None:
#                 send_data(latitude, longitude, mac_address, sos_triggered)
#         else:
#             print("SOS is already off.")

#     time.sleep(0.1)  # Poll buttons every 100ms