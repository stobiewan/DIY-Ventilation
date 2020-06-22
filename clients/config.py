from machine import Pin

from clients.mqtt_as import config

config['server'] = '192.168.0.0'  # Change to suit

# Not needed if you're only using ESP8266
config['ssid'] = 'todo'
config['wifi_pw'] = 'todo'


def ledfunc(pin):
    pin = pin

    def func(v):
        pin(not v)  # Active low on ESP8266

    return func


set_led = ledfunc(Pin(2, Pin.OUT, value=1))  # Message received
