import time
import uasyncio as asyncio
from machine import Pin

from common.common import *
from clients.config import set_led
from clients.config import config
from clients.mqtt_as import MQTTClient
from clients.sht30 import SHT30
from clients.sht30 import SHT30Error


valve_moving_period = 20
valves_state = ValveStates.unknown
sensor_topic = Topic.ROOF_TEMP_HUM
fan_low_pin = Pin(12, Pin.OUT)  # D6
fan_high_pin = Pin(13, Pin.OUT)  # D7
valves_extract_roof_pin = Pin(14, Pin.OUT)  # D5
valves_extract_living_pin = Pin(15, Pin.OUT)  # D8
fan_low_pin.off()
fan_high_pin.off()
valves_extract_roof_pin.off()
valves_extract_living_pin.off()


def set_fan(mode):
    if mode == FanSpeeds.OFF:
        fan_low_pin.off()
        fan_high_pin.off()
    elif mode == FanSpeeds.LOW:
        fan_low_pin.on()
        fan_high_pin.off()
    elif mode == FanSpeeds.HIGH:
        fan_low_pin.off()
        fan_high_pin.on()


def set_valves(mode):
    global valves_state
    if mode == valves_state or valves_state == ValveStates.transitioning:
        return  # duplicate msg
    else:
        valves_state = ValveStates.transitioning
    if mode == ValveStates.extract_from_living:
        valves_extract_living_pin.on()
    elif mode == ValveStates.extract_from_roof:
        valves_extract_roof_pin.on()
    time.sleep(valve_moving_period)
    valves_state = mode
    valves_extract_roof_pin.off()
    valves_extract_living_pin.off()


def subscription_callback(topic, msg, retained):
    # Act on received messages here
    topic = int(topic)
    msg = int(msg)
    if topic == Topic.SET_FAN:
        set_fan(msg)
    if topic == Topic.SET_VALVES:
        set_valves(msg)


async def connect_coroutine(client):
    # Subscribe here so subs are renewed on reconnect
    await client.subscribe(str(Topic.SET_FAN), 1)
    await client.subscribe(str(Topic.SET_VALVES), 1)


async def main(client):
    connected = False
    while not connected:
        try:
            await client.connect()
            connected = True
            set_led(0)
        except OSError:
            set_led(1)
            await asyncio.sleep(sleep_period_seconds)

    sensor = SHT30()
    while True:
        await asyncio.sleep(sleep_period_seconds)
        success = client.isconnected()
        if success:
            try:
                temperature, humidity = sensor.measure()
                await client.publish(str(sensor_topic), '{} {}'.format(temperature, humidity), qos=0)
            except (TypeError, SHT30Error):
                success = False
        set_led(int(not success))


def run():
    config['subs_cb'] = subscription_callback
    config['connect_coro'] = connect_coroutine

    MQTTClient.DEBUG = False
    client = MQTTClient(config)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(client))
    finally:
        client.close()  # Prevent LmacRxBlk:1 errors
