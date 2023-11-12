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
from adafruit_httpserver import Server, Request, Response, POST
from prometheus_express import start_http_server, CollectorRegistry, Counter, Gauge, Router


ssid="network"
passwd="password"

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
metric_g = Gauge('test_gauge',
                    'a test gauge',
                     labels=['source'],
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
    time.sleep(0.1)
    
    metric_c.labels('heartbeat').inc(1)
    metric_c.labels('random').inc(4)
    metric_g.labels('clock').set(time.time())
    metric_g.labels('random').set(4)
    
    server.poll()
    

