import time
import ipaddress
import wifi
import socketpool
import ssl
import adafruit_requests
import board
import digitalio
import adafruit_ahtx0
import wifi_details

from analogio import AnalogIn
from adafruit_httpserver import Server, Request, Response, POST
from prometheus_express import start_http_server, CollectorRegistry, Counter, Gauge, Router

def get_voltage(pin):
    return (pin.value * 3.3) / 65536

def get_on(pin):
    return get_voltage(pin) > 0.01

ssid=wifi_details.SSID
passwd=wifi_details.PASSWORD

basement_in = AnalogIn(board.A1)
main_in = AnalogIn(board.A2)
upper_in = AnalogIn(board.A3)

sensor = None
try:
    sensor = adafruit_ahtx0.AHTx0(board.I2C())
except:
    print("no sensor")

basement_pin = digitalio.DigitalInOut(board.IO9)
main_pin = digitalio.DigitalInOut(board.IO10)
upper_pin = digitalio.DigitalInOut(board.IO11)
basement_pin.direction = digitalio.Direction.OUTPUT
main_pin.direction = digitalio.Direction.OUTPUT
upper_pin.direction = digitalio.Direction.OUTPUT
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

basement_on = False
main_on = False
upper_on = False

basement_pin.value = True
main_pin.value = True
upper_pin.value = True

readings = {"basement": [], "main": [], "upper": []}

for network in wifi.radio.start_scanning_networks():
    print(network, network.ssid, network.channel)
wifi.radio.stop_scanning_networks()

print("joining network...")
print(wifi.radio.connect(ssid=ssid,password=passwd))
# the above gives "ConnectionError: Unknown failure" if ssid/passwd is wrong

print("my IP addr:", wifi.radio.ipv4_address)
print("my MAC addr:", wifi.radio.mac_address)

print("pinging 192.168.0.117...")
ip1 = ipaddress.ip_address("192.168.0.117")
print("ip1:",ip1)
print("ping:", wifi.radio.ping(ip1))

registry = CollectorRegistry(namespace='environment')

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
                     
metric_laundry_temperature = Gauge('temperature_laundry',
                    'a temperature gauge in the laundry room',
                     labels=['temperature_laundry'],
                     registry=registry)
                     
metric_laundry_humidity = Gauge('humidity_laundry',
                    'a humidity gauge in the laundry room',
                     labels=['humidity_laundry'],
                     registry=registry)                     

router = Router()
router.register('GET', '/metrics', registry.handler)
server = False

pool = socketpool.SocketPool(wifi.radio)
request = adafruit_requests.Session(pool, ssl.create_default_context())

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

upper_pin.value = False
main_pin.value = False
basement_pin.value = False

while True:
    
    readings["basement"].append(str(get_on(basement_in)))
    readings["main"].append(str(get_on(main_in)))
    readings["upper"].append(str(get_on(upper_in)))
    
    printLog = False
    
    if(len(readings["basement"])) > 30:
        printLog = True
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
    
        if printLog:
            print("Basement: " + str(basement_on) + " Main: " + str(main_on) + " Upper: " + str(upper_on))
        if sensor:
            print("\nTemperature: %0.1f C" % sensor.temperature)
            print("Humidity: %0.1f %%" % sensor.relative_humidity)
            print("Humidity: %0.1f %%" % sensor.relative_humidity)

    time.sleep(0.1)
    
    if sensor:
        metric_laundry_temperature.labels('temperature_laundry').set(sensor.temperature)
        metric_laundry_humidity.labels('humidity_laundry').set(sensor.relative_humidity)
    
    if basement_on:
        metric_basement.labels('thermostat_basement_heat').set(1)
        basement_pin.value = True
    else:
        metric_basement.labels('thermostat_basement_heat').set(0)
        basement_pin.value = False
    if main_on:
        metric_main.labels('thermostat_main_heat').set(1)
        main_pin.value = True
    else:
        metric_main.labels('thermostat_main_heat').set(0)
        main_pin.value = False
    if upper_on:
        metric_upper.labels('thermostat_upper_heat').set(1)
        upper_pin.value = True
    else:
        metric_upper.labels('thermostat_upper_heat').set(0)
        upper_pin.value = False

    server.poll()
    
    led.value = not led.value
