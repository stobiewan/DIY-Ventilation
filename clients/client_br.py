import uasyncio as asyncio

from common.common import *
from clients.config import set_led
from clients.config import config
from clients.mqtt_as import MQTTClient
from clients.sht30 import SHT30
from clients.sht30 import SHT30Error


sensor_topic = Topic.BR_TEMP_HUM


def subscription_callback(topic, msg, retained):
    # Act on received messages here
    pass


async def connect_coroutine(client):
    # Subscribe here so subs are renewed on reconnect
    pass


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
