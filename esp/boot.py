import time
import socket
import network
from machine import Timer, Pin, WDT


WIFI_NETWORK = "milkyway"
WIFI_PASSWORD = "qwertyuiop123"

STA_IF = network.WLAN(network.STA_IF)


def connect_to_wifi(ssid, password):
    print("Connecting to WiFi")
    STA_IF.active(True)
    STA_IF.connect(ssid, password)
    start_time = time.time()
    while time.time() - start_time < 30:
        if STA_IF.isconnected():
            print("Connected to WiFi")
            return True
        else:
            time.sleep(1)
    else:
        print("!!! Failed to connect to WiFi")
        return False


def check_connection():
    print("Checking connection")
    if not STA_IF.isconnected():
        print("!!! Not connected to WiFi")
        connect_to_wifi(WIFI_NETWORK, WIFI_PASSWORD)


def check_wifi_connect_regularly():
    print("Add task to check wifi connection regularly")
    timer = Timer(-1)
    timer.init(period=60000, mode=Timer.PERIODIC, callback=check_connection)


def disable_pins():
    for pin_number in (12, 13, 14, 16):
        pin = Pin(pin_number, Pin.OUT)
        pin.off()


def feed_wdt(z):
    WDT().feed()


def enable_wdt():
    tim1 = Timer(-1)
    tim1.init(period=1000, mode=Timer.PERIODIC, callback=feed_wdt)


def start_socket_server():
    # format: on|off pin_number,pin_number
    print("Start socket server")
    s = socket.socket()
    ai = socket.getaddrinfo("0.0.0.0", 8080)
    addr = ai[0][-1]
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)

    while True:
        print("While loop")
        conn, addr = s.accept()
        print("Got a connection from %s" % str(addr))
        request = conn.recv(1024).decode()
        print('Content = "%s"' % request)

        d = request.split()
        response = ""

        if len(d) == 2:
            action = d[0].strip()
            pins = d[1].split(',')

            if action not in ["on", "off"]:
                response = "Invalid action"
            else:
                for pin_number in pins:
                    pin = Pin(int(pin_number), Pin.OUT)
                    if action == "on":
                        pin.on()
                    elif action == "off":
                        pin.off()
                response = "Done"
        elif len(d) == 1:
            action = d[0].strip()
            if action == "uptime":
                response = str(time.time())
            elif action == "status":
                response = ""
                for pin_number in (12, 13, 14, 16):
                    pin = Pin(pin_number)
                    response += f"{pin_number}={pin.value()};"
            else:
                response = "Invalid request"
        else:
            response = "Invalid request"
        conn.sendall(response)
        conn.close()


disable_pins()
connect_to_wifi(WIFI_NETWORK, WIFI_PASSWORD)
# check_wifi_connect_regularly()
enable_wdt()
start_socket_server()
