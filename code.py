# Write your code here :-)
# esp32s2-test.py -- small WiFi test program for ESP32-S2 CircuitPython 6
# taken from https://www.reddit.com/r/circuitpython/comments/ianpm8/using_wifi_when_running_on_esp32s2saola1_board/
#
import time
import ipaddress
import wifi
import socketpool
import ssl
import adafruit_requests
import board

from analogio import AnalogIn
from adafruit_httpserver import Server, Request, Response, POST
from prometheus_express import start_http_server, CollectorRegistry, Counter, Gauge, Router


def get_voltage(pin):
    return (pin.value * 3.3) / 65536

def get_on(pin):
    return get_voltage(pin) > 0.01

ssid="xxxxxxxx"
passwd="xxxxxxxx"

basement_in = AnalogIn(board.A1)
main_in = AnalogIn(board.A2)
upper_in = AnalogIn(board.A3)

basement_on = False
main_on = False
upper_on = False

readings = {"basement": [], "main": [], "upper": []}

print('Hello World!')

for network in wifi.radio.start_scanning_networks():
    print(network, network.ssid, network.channel)
wifi.radio.stop_scanning_networks()

print("joining network...")
print(wifi.radio.connect(ssid=ssid,password=passwd))
# the above gives "ConnectionError: Unknown failure" if ssid/passwd is wrong

print("my IP addr:", wifi.radio.ipv4_address)
#print("my MAC addr:", wifi.radio.mac_address)


print("pinging 192.168.0.115...")
ip1 = ipaddress.ip_address("192.168.0.115")
print("ip1:",ip1)
print("ping:", wifi.radio.ping(ip1))

registry = CollectorRegistry(namespace='prom_express')
metric_c = Counter('test_counter',
                    'a test counter',
                    labels=['source'],
                    registry=registry)
metric_basement = Gauge('thermostat_basement_heat',
                    'a thermostat_basement_heat gauge',
                     labels=['thermostat_basement_heat'],
                     registry=registry)

metric_main = Gauge('thermostat_main_heat',
                    'a thermostat_main_heat gauge',
                     labels=['thermostat_main_heat'],
                     registry=registry)

metric_upper = Gauge('thermostat_upper_heat',
                    'a thermostat_upper_heat gauge',
                     labels=['thermostat_upper_heat'],
                     registry=registry)


router = Router()
router.register('GET', '/metrics', registry.handler)
server = False

pool = socketpool.SocketPool(wifi.radio)
request = adafruit_requests.Session(pool, ssl.create_default_context())

#server_port=8080

#server = start_http_server(server_port, address=str(wifi.radio.ipv4_address), depth=8)


print("Fetching wifitest.adafruit.com...");
response = request.get("http://wifitest.adafruit.com/testwifi/index.html")
print(response.status_code)
print(response.text)

print("Fetching https://httpbin.org/get...");
response = request.get("https://httpbin.org/get")
print(response.status_code)
print(response.json())

server = Server(pool, "/static", debug=True)

print("starting server..")
# startup the server
try:
    server.start(str(wifi.radio.ipv4_address))
    print("Listening on http://%s:80" % wifi.radio.ipv4_address)
#  if the server fails to begin, restart the pico w
except OSError:
    time.sleep(5)
    print("restarting..")
    microcontroller.reset()


#  route default static IP
@server.route("/")
def base(request: Request):  # pylint: disable=unused-argument
    #  serve the HTML f string
    #  with content type text/html
    return Response(request, f"{webpage()}", content_type='text/html')



@server.route("/metrics")
def metrics(request:Request):
    resp = registry.render()
    text = ""
    for line in resp:
        text += line + "\n"
    return Response(request, f"{text}", content_type='text/html')

def webpage():
    text = "<html><body>hello world </body></html>"
    return text

while True:
    #print("alive")
    readings["basement"].append(str(get_on(basement_in)))
    readings["main"].append(str(get_on(main_in)))
    readings["upper"].append(str(get_on(upper_in)))

    #print(str(get_on(basement_in)) + " " + str(get_on(main_in)) + " " + str(get_on(upper_in)))


    if(len(readings["basement"])) > 30:
        if str(True) in readings["basement"]:
            basement_on = True
        else:
            basement_on = False
        readings["basement"].clear()
    if(len(readings["main"])) > 30:
        if str(True) in readings["main"]:
            main_on = True
        else:
            main_on = False
        readings["main"].clear()
    if(len(readings["upper"])) > 30:
        if str(True) in readings["upper"]:
            upper_on = True
        else:
            upper_on = False
        readings["upper"].clear()

    #print(str((get_voltage(analog_in1)) > 0.01) + " " + str((get_voltage(analog_in2)) > 0.01)+ " " + str((get_voltage(analog_in3)) > 0.01))

    print(str(basement_on) + " " + str(main_on) + " " + str(upper_on))

    time.sleep(0.1)

    if basement_on:
        metric_basement.labels('thermostat_basement_heat').set(1)
    else:
        metric_basement.labels('thermostat_basement_heat').set(0)
    if main_on:
        metric_main.labels('thermostat_main_heat').set(1)
    else:
        metric_main.labels('thermostat_main_heat').set(0)
    if upper_on:
        metric_upper.labels('thermostat_upper_heat').set(1)
    else:
        metric_upper.labels('thermostat_upper_heat').set(0)

    server.poll()


