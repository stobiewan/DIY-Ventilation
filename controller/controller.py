import threading
import time

from paho.mqtt import client as mqtt

from . import event_selector
from . import hardware_state_machine
from common.common import *
from web_ui import ui_server


class RoomData:
    def __init__(self, bytes_string):
        temp_bs, hum_bs = bytes_string.split()
        self.temp = float(temp_bs)
        self.humidity = float(hum_bs)


class DatedData:
    def __init__(self):
        self._data = None
        self.timestamp = 0

    @property
    def data(self):
        if self.is_fresh():
            return self._data
        else:
            return None

    @data.setter
    def data(self, value):
        self._data = value
        self.timestamp = time.time()

    def is_fresh(self):
        return time.time() - self.timestamp < sleep_period_seconds * 2  # allow one missed report

    def get_temp(self):
        d = self.data
        if d is not None:
            d = d.temp
        return d

    def get_humidity(self):
        d = self.data
        if d is not None:
            d = d.humidity
        return d


class ClimateState:
    def __init__(self):
        self.bdrm_data = DatedData()
        self.lvrm_data = DatedData()
        self.roof_data = DatedData()
        self.outside_temp = DatedData()  # not used yet

    def is_fresh(self):
        return all([self.lvrm_data.is_fresh(), self.roof_data.is_fresh(), self.bdrm_data.is_fresh()])

    def process_update(self, topic, payload):
        if topic == Topic.BR_TEMP_HUM:
            self.bdrm_data.data = RoomData(payload)
        if topic == Topic.LR_TEMP_HUM:
            self.lvrm_data.data = RoomData(payload)
        if topic == Topic.ROOF_TEMP_HUM:
            self.roof_data.data = RoomData(payload)


class Controller(mqtt.Client):
    def __init__(self):
        self.broker_address = '127.0.0.1'
        self.hardware_state = hardware_state_machine.HardwareState()
        self.climate_state = ClimateState()
        self.event_selector = event_selector.EventSelector()
        self.target_temperature = 21
        self._hard_flush_requested = False  # locks used as reads and writes from both flask and controller threads
        self.enabled = True
        super().__init__()
        self.lock = threading.RLock()
        thread = threading.Thread(target=self.start_web_server, args=())
        thread.start()

    def _lock(func):
        def wrapper(self, *args, **kwargs):
            self.lock.acquire()
            r = func(self, *args, **kwargs)
            self.lock.release()
            return r
        return wrapper

    def on_connect(self, mqttc, obj, flags, rc):
        print("rc: "+str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        self.subscribe(str(Topic.BR_TEMP_HUM))
        self.subscribe(str(Topic.LR_TEMP_HUM))
        self.subscribe(str(Topic.ROOF_TEMP_HUM))

    def on_message(self, mqttc, obj, msg):
        print('on_message: ' + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        topic = int(msg.topic)
        self.climate_state.process_update(topic, msg.payload)

    def on_publish(self, client, obj, mid):
        print("mid: "+str(mid))

    def on_subscribe(self, client, obj, mid, granted_qos):
        print("Subscribed: "+str(mid)+" "+str(granted_qos))

    def on_log(self, client, obj, level, string):
        print(string)

    @_lock
    def analyse_state(self):
        trigger_str = self.event_selector.select_event(self.enabled, self.climate_state.is_fresh(),
                                                       self.climate_state, self.get_hard_flush_requested(),
                                                       self.target_temperature)
        trigger_method = getattr(self.hardware_state, trigger_str)
        trigger_method()
        while len(self.hardware_state.pending_actions) > 0:
            action = self.hardware_state.pending_actions.popleft()
            self.perform_action(action)
        self.set_flush_request_handled()

    def perform_action(self, action):
        if action == hardware_state_machine.Actions.FAN_OFF:
            self.publish(str(Topic.SET_FAN), payload=FanSpeeds.OFF, qos=1)
        if action == hardware_state_machine.Actions.FAN_LOW:
            self.publish(str(Topic.SET_FAN), payload=FanSpeeds.LOW, qos=1)
        if action == hardware_state_machine.Actions.FAN_HIGH:
            self.publish(str(Topic.SET_FAN), payload=FanSpeeds.HIGH, qos=1)
        if action == hardware_state_machine.Actions.VALVES_EXTRACT_ROOF:
            self.publish(str(Topic.SET_VALVES), payload=ValveStates.extract_from_roof, qos=1)
        if action == hardware_state_machine.Actions.VALVES_EXTRACT_LVRM:
            self.publish(str(Topic.SET_VALVES), payload=ValveStates.extract_from_living, qos=1)

    def run(self):
        self.connect(self.broker_address)
        self.loop_start()

        while True:
            time.sleep(sleep_period_seconds)
            self.analyse_state()

    def start_web_server(self):
        ui_server.run_app(self)

    @_lock
    def increase_target_temp(self):
        self.target_temperature += 1
        if self.target_temperature > 30:
            self.target_temperature = 30

    @_lock
    def decrease_target_temp(self):
        self.target_temperature -= 1
        if self.target_temperature < 10:
            self.target_temperature = 10

    @_lock
    def request_flush(self):
        self._hard_flush_requested = True

    @_lock
    def set_flush_request_handled(self):
        self._hard_flush_requested = False

    @_lock
    def get_hard_flush_requested(self):
        return self._hard_flush_requested

    @_lock
    def toggle_enable(self):
        self.enabled = not self.enabled

# diagnostic methods for buttons which manually control hardware when system is disabled.
# these will break the state machine and should be used with care.
    @_lock
    def diagnostic_extract_living(self):
        if self.enabled:
            raise DiagnosticsError
        self.publish(str(Topic.SET_VALVES), payload=ValveStates.extract_from_living, qos=0)

    @_lock
    def diagnostic_extract_roof(self):
        if self.enabled:
            raise DiagnosticsError
        self.publish(str(Topic.SET_VALVES), payload=ValveStates.extract_from_roof, qos=0)

    @_lock
    def diagnostic_fan_off(self):
        if self.enabled:
            raise DiagnosticsError
        self.publish(str(Topic.SET_FAN), payload=FanSpeeds.OFF, qos=0)

    @_lock
    def diagnostic_fan_low(self):
        if self.enabled:
            raise DiagnosticsError
        self.publish(str(Topic.SET_FAN), payload=FanSpeeds.LOW, qos=0)

    @_lock
    def diagnostic_fan_high(self):
        if self.enabled:
            raise DiagnosticsError
        self.publish(str(Topic.SET_FAN), payload=FanSpeeds.HIGH, qos=0)


class DiagnosticsError(Exception):
    pass


def run_mqtt_controller():
    mqttc = Controller()
    mqttc.run()
