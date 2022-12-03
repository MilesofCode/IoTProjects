# Imports
from umqtt.robust import MQTTClient
import time
import ujson
from time import sleep
import dht
import sds011
from machine import Pin, UART

# AWS settings
HOST = "weather_station(can be whatever name you want)"
REGION = "AWS REGION"
MQTT_HOST = "YOUR_AWS_IOT_ENDPOINT"  #Your AWS IoT endpoint

CERT_FILE = "/device_certificate.pem.crt"  #the ".crt" may be hidden that’s ok
KEY_FILE = "/private_key.key"

MQTT_CLIENT_ID = "weather_station"
MQTT_PORT = 8883 #MQTT secured

PUB_TOPIC = "iot/outTopic" #coming out of device
SUB_TOPIC = "iot/inTopic"  #coming into device

# SDS011 worrks with uart. Set pins used for uart on ESP32
uart = UART(1, baudrate = 9600, rx = 5, tx = 4)
dust_sensor = sds011.SDS011(uart)
dust_sensor.sleep()

# Create a DHT sensor object and call methods to get values
sensor = dht.DHT22(Pin(2))
sensor.measure()
temp = sensor.temperature() * 9/5 + 32
humidity = sensor.humidity()


WIFI_SSID = "Name Of WIFI Here"
WIFI_PW = "Password to wifi here"

MQTT_CLIENT = None

print("starting program")

# Function to connect to local wi-fi
def network_connect():
    print("starting connection method")
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(WIFI_SSID , WIFI_PW)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())


    
def pub_msg(msg):  #publish is synchronous so we poll and publish
    global MQTT_CLIENT
    try:    
        MQTT_CLIENT.publish(PUB_TOPIC, msg)
        print("Sent: " + msg)
    except Exception as e:
        print("Exception publish: " + str(e))
        raise

def sub_cb(topic, msg):
    print('Device received a Message: ')
    print((topic, msg))  #print incoming message, waits for loop below
    pin.value(0)         #blink if incoming message by toggle off

def device_connect():    
    global MQTT_CLIENT

    try:  #all this below runs once, equivalent to Arduino's "setup" function)
        with open(KEY_FILE, "r") as f: 
            key = f.read()
        print("Got Key")
       
        with open(CERT_FILE, "r") as f: 
            cert = f.read()
        print("Got Cert")

        MQTT_CLIENT = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_HOST, port=MQTT_PORT, keepalive=5000, ssl=True, ssl_params={"cert":cert, "key":key, "server_side":False})
        MQTT_CLIENT.connect()
        print('MQTT Connected')
        MQTT_CLIENT.set_callback(sub_cb)
        MQTT_CLIENT.subscribe(SUB_TOPIC)
        print('Subscribed to %s as the incoming topic' % (SUB_TOPIC))
        return MQTT_CLIENT
    except Exception as e:
        print('Cannot connect MQTT: ' + str(e))
        raise


#start execution
try:
    print("Connecting WIFI")
    network_connect()
    print("Connecting MQTT")
    device_connect()
    while True: #loop forever
            pending_message = MQTT_CLIENT.check_msg()  # check for new subscription payload incoming
            if pending_message != 'None':  #check if we have a message
                dust_sensor.wake()
                time.sleep(5)
                #     #Returns NOK if no measurement found in reasonable time
                status = dust_sensor.read()
                #Returns NOK if checksum failed
                pkt_status = dust_sensor.packet_status
                #Stop fan
                dust_sensor.sleep()
                sensor.measure()
                temp = sensor.temperature() * 9/5 + 32
                humidity = sensor.humidity()
                deviceTime = time.time()
                values = {"temperature": temp,
                          "humidity": humidity,
                          "pm2.5": dust_sensor.pm25,
                          "pm10": dust_sensor.pm10}
                pm25 = dust_sensor.pm25
                pm10 = dust_sensor.pm10
                print("Publishing")
#                 pub_msg(ujson.dumps(values))
                pub_msg("{\n  \"temperature\": %d,\n  \"humidity\": %d,\n \"pm25\": %d,\n \"pm10\": %d \n}"%(temp,humidity,pm25,pm10))
                print("published payload")
                time.sleep(5)  #A 5 second delay between publishing, adjust as you like
            
except Exception as e:
    print(str(e))