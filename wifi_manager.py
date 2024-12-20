import time
import network
import socket
import ujson
from machine import reset
import machine
import os

# HTML content for WiFi configuration page
wifi_portal_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Manager</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 300px; margin: 0 auto; text-align: center;">
    <h1 style="color: #333; font-size: 24px;">Configure WiFi</h1>
    <form action="/configure" method="post" style="display: flex; flex-direction: column; gap: 10px;">
        <label for="ssid" style="font-size: 16px; color: #333;">Select Network:</label>
        <select name="ssid" id="ssid" style="padding: 8px; font-size: 16px; border-radius: 4px; border: 1px solid #ccc;">
            {options}
        </select>

        <label for="password" style="font-size: 16px; color: #333;">Password:</label>
        <input type="password" id="password" name="password" placeholder="Enter WiFi password" 
               style="padding: 8px; font-size: 16px; border-radius: 4px; border: 1px solid #ccc;">

        <input type="submit" value="Connect" 
               style="padding: 10px; font-size: 16px; border-radius: 4px; background-color: #4CAF50; color: white; border: none; cursor: pointer;">
    </form>
</body>
</html>
"""



# Scan for available WiFi networks and create options list
def generate_options():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    options = ""
    for net in networks:
        ssid = net[0].decode('utf-8')
        options += f"<option value='{ssid}'>{ssid}</option>"
    return options

# Set up the Access Point for configuration
def start_access_point():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="GPS_WifiConfig", authmode=network.AUTH_OPEN)
    print("Access point established. Connect to 'GPS_WifiConfig' to configure WiFi.")
    return ap

# Web server to handle WiFi configuration
def start_web_server(): 
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server started on http://192.168.4.1")

    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024).decode('utf-8')
        
        # Serve HTML form
        if "GET / " in request:
            options = generate_options()
            response = wifi_portal_html.format(options=options)
            cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
            cl.send(response)
        
        # Handle form submission
        elif "POST /configure" in request:
            # Parse form data
            params = request.split("\r\n\r\n")[1]
            ssid = params.split("&")[0].split("=")[1]
            password = params.split("&")[1].split("=")[1]

            # Decode URL-encoded SSID and password
            ssid = ssid.replace("%20", " ")
            password = password.replace("%20", " ")

            print("Received WiFi credentials:")
            print("SSID:", ssid)
            print("Password:", password)
            
            # Save WiFi credentials
            with open("wifi_config.json", "w") as f:
                f.write(ujson.dumps({"ssid": ssid, "password": password}))
            
            cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n")
            cl.send("WiFi credentials saved. ESP32 will restart and connect.")
            cl.close()
            time.sleep(2)
            machine.reset()  # Restart ESP32 to connect with new WiFi credentials
        
        cl.close()

# Connect to WiFi using saved credentials
def connect_to_saved_wifi():
    try:
        with open("wifi_config.json", "r") as f:
            config = ujson.load(f)
            ssid = config["ssid"]
            password = config["password"]
    except OSError:
        print("No WiFi credentials found.")
        return False
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    
    for attempt in range(10):  # Try connecting for 10 seconds
        if wlan.isconnected():
            print("Connected to WiFi:", wlan.ifconfig())
            return True
        time.sleep(1)
    
    print("Failed to connect to WiFi. Erasing saved credentials.")
    erase_saved_credentials()  # Erase credentials if connection fails
    machine.reset()  # Reset ESP32 to re-enter WiFi configuration mode
    return False

# Erase saved WiFi credentials
def erase_saved_credentials():
    try:
        os.remove("wifi_config.json")
        print("Saved credentials erased.")
    except OSError:
        print("No credentials file to erase.")

# Main program
if __name__ == "__main__":
    if not connect_to_saved_wifi():  # If no saved WiFi credentials or unable to connect
        ap = start_access_point()
        start_web_server()  # Start the configuration portal
    else:
        print("Connected to WiFi.")
        # Continue with your application logic here
