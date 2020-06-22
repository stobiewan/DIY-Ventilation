"""
Architecture description:
Controller communicates with microcontrollers to get temps and humidity, then judges best event, then instructs micros.
Event is passed to state machine which manages transitions and defines state to send to micros.
Micros periodically send climate data and listen for instructions to set fan and valves. State is stored to handle
    duplicate messages without repeating actions.
"""

import enum
import time
from collections import deque

from transitions import Machine

from common.common import sleep_period_seconds


five_minutes = 60 * 5 - sleep_period_seconds / 2
fifteen_minutes = 60 * 15 - sleep_period_seconds / 2
hour_in_seconds = 60 * 60 - sleep_period_seconds / 2
roof_ideal_str = 'roof_ideal'  # ideal will turn on and use fast fan.
lvrm_ideal_str = 'lvrm_ideal'
roof_good__str = 'roof_good_'  # good will turn on and use slow fan.
lvrm_good__str = 'lvrm_good_'
roof_go_on_str = 'roof_go_on'  # go_on will continue an already on fan but won't start from idle.
lvrm_go_on_str = 'lvrm_go_on'
roof_worst_str = 'roof_worst'
lvrm_worst_str = 'lvrm_worst'
hard_flush_str = 'hard_flush'
force_idle_str = 'force_idle'


class Actions(enum.Enum):
    FAN_OFF = 0
    FAN_LOW = 1
    FAN_HIGH = 2
    VALVES_EXTRACT_ROOF = 3
    VALVES_EXTRACT_LVRM = 4


class HardwareState(Machine):
    states = ['idle', 'slow_ex_roof', 'slow_ex_lvrm', 'fast_ex_roof', 'fast_ex_lvrm']
    transitions = [
        {'trigger': roof_ideal_str, 'source': 'idle', 'dest': 'slow_ex_roof'},
        {'trigger': lvrm_ideal_str, 'source': 'idle', 'dest': 'slow_ex_lvrm'},
        {'trigger': roof_good__str, 'source': 'idle', 'dest': 'slow_ex_roof'},
        {'trigger': lvrm_good__str, 'source': 'idle', 'dest': 'slow_ex_lvrm'},
        {'trigger': roof_go_on_str, 'source': 'idle', 'dest': 'slow_ex_roof', 'conditions': 'flush_needed', 'before': 'set_flushing'},
        {'trigger': lvrm_go_on_str, 'source': 'idle', 'dest': 'slow_ex_lvrm', 'conditions': 'flush_needed', 'before': 'set_flushing'},
        {'trigger': roof_worst_str, 'source': 'idle', 'dest': 'slow_ex_lvrm', 'conditions': 'flush_needed', 'before': 'set_flushing'},
        {'trigger': lvrm_worst_str, 'source': 'idle', 'dest': 'slow_ex_roof', 'conditions': 'flush_needed', 'before': 'set_flushing'},
        {'trigger': hard_flush_str, 'source': 'idle', 'dest': 'fast_ex_roof', 'before': 'set_hard_flushing'},
        {'trigger': force_idle_str, 'source': 'idle', 'dest': 'idle', 'conditions': 'never'},

        {'trigger': roof_ideal_str, 'source': 'slow_ex_roof', 'dest': 'fast_ex_roof', 'conditions': 'slow_trial_done'},
        {'trigger': lvrm_ideal_str, 'source': 'slow_ex_roof', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': roof_good__str, 'source': 'slow_ex_roof', 'dest': 'slow_ex_roof', 'conditions': 'never'},
        {'trigger': lvrm_good__str, 'source': 'slow_ex_roof', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': roof_go_on_str, 'source': 'slow_ex_roof', 'dest': 'slow_ex_roof', 'conditions': 'never'},
        {'trigger': lvrm_go_on_str, 'source': 'slow_ex_roof', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': roof_worst_str, 'source': 'slow_ex_roof', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': lvrm_worst_str, 'source': 'slow_ex_roof', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': hard_flush_str, 'source': 'slow_ex_roof', 'dest': 'fast_ex_roof', 'before': 'set_hard_flushing'},
        {'trigger': force_idle_str, 'source': 'slow_ex_roof', 'dest': 'idle'},

        {'trigger': roof_ideal_str, 'source': 'slow_ex_lvrm', 'dest': 'idle'},
        {'trigger': lvrm_ideal_str, 'source': 'slow_ex_lvrm', 'dest': 'fast_ex_lvrm', 'conditions': 'slow_trial_done'},
        {'trigger': roof_good__str, 'source': 'slow_ex_lvrm', 'dest': 'idle'},
        {'trigger': lvrm_good__str, 'source': 'slow_ex_lvrm', 'dest': 'slow_ex_lvrm', 'conditions': 'never'},
        {'trigger': roof_go_on_str, 'source': 'slow_ex_lvrm', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': lvrm_go_on_str, 'source': 'slow_ex_lvrm', 'dest': 'slow_ex_lvrm', 'conditions': 'never'},
        {'trigger': roof_worst_str, 'source': 'slow_ex_lvrm', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': lvrm_worst_str, 'source': 'slow_ex_lvrm', 'dest': 'idle', 'conditions': 'flush_done'},
        {'trigger': hard_flush_str, 'source': 'slow_ex_lvrm', 'dest': 'fast_ex_roof', 'before': 'set_hard_flushing'},
        {'trigger': force_idle_str, 'source': 'slow_ex_lvrm', 'dest': 'idle'},

        {'trigger': roof_ideal_str, 'source': 'fast_ex_roof', 'dest': 'fast_ex_roof', 'conditions': 'never'},
        {'trigger': lvrm_ideal_str, 'source': 'fast_ex_roof', 'dest': 'idle', 'conditions': 'hard_flush_done'},
        {'trigger': roof_good__str, 'source': 'fast_ex_roof', 'dest': 'slow_ex_roof'},
        {'trigger': lvrm_good__str, 'source': 'fast_ex_roof', 'dest': 'idle', 'conditions': 'hard_flush_done'},
        {'trigger': roof_go_on_str, 'source': 'fast_ex_roof', 'dest': 'slow_ex_roof'},
        {'trigger': lvrm_go_on_str, 'source': 'fast_ex_roof', 'dest': 'idle', 'conditions': 'hard_flush_done'},
        {'trigger': roof_worst_str, 'source': 'fast_ex_roof', 'dest': 'idle', 'conditions': 'hard_flush_done'},
        {'trigger': lvrm_worst_str, 'source': 'fast_ex_roof', 'dest': 'idle', 'conditions': 'hard_flush_done'},
        {'trigger': hard_flush_str, 'source': 'fast_ex_roof', 'dest': 'fast_ex_roof', 'before': 'set_hard_flushing'},
        {'trigger': force_idle_str, 'source': 'fast_ex_roof', 'dest': 'idle'},

        {'trigger': roof_ideal_str, 'source': 'fast_ex_lvrm', 'dest': 'idle'},
        {'trigger': lvrm_ideal_str, 'source': 'fast_ex_lvrm', 'dest': 'fast_ex_lvrm', 'conditions': 'never'},
        {'trigger': roof_good__str, 'source': 'fast_ex_lvrm', 'dest': 'idle'},
        {'trigger': lvrm_good__str, 'source': 'fast_ex_lvrm', 'dest': 'slow_ex_lvrm'},
        {'trigger': roof_go_on_str, 'source': 'fast_ex_lvrm', 'dest': 'idle'},
        {'trigger': lvrm_go_on_str, 'source': 'fast_ex_lvrm', 'dest': 'slow_ex_lvrm'},
        {'trigger': roof_worst_str, 'source': 'fast_ex_lvrm', 'dest': 'idle'},
        {'trigger': lvrm_worst_str, 'source': 'fast_ex_lvrm', 'dest': 'idle'},
        {'trigger': hard_flush_str, 'source': 'fast_ex_lvrm', 'dest': 'fast_ex_roof', 'before': 'set_hard_flushing'},
        {'trigger': force_idle_str, 'source': 'fast_ex_lvrm', 'dest': 'idle'},
    ]

    def __init__(self):
        Machine.__init__(self, states=self.states, initial='idle', transitions=self.transitions,
                         after_state_change=self.set_state_start_time_and_update_flushing)
        self.state_start_time = time.time()
        self.pending_actions = deque([])
        self.flushing = False  # flush caused by timer
        self.hard_flushing = False  # flush forced by user input via web UI

    def set_state_start_time_and_update_flushing(self):
        self.state_start_time = time.time()
        if self.state not in ['slow_ex_roof', 'slow_ex_lvrm']:
            self.flushing = False
        if self.state not in ['fast_ex_roof']:
            self.hard_flushing = False

    def get_state_age(self):
        now = time.time()
        age = now - self.state_start_time
        return age

    def set_flushing(self):
        self.flushing = True

    def set_hard_flushing(self):
        self.hard_flushing = True

    # conditions
    def never(self):
        return False

    def flush_done(self):
        return (self.get_state_age() > fifteen_minutes) or (self.flushing is False)

    def hard_flush_done(self):
        return (self.get_state_age() > fifteen_minutes) or (self.hard_flushing is False)

    def flush_needed(self):
        return self.state == 'idle' and self.get_state_age() > hour_in_seconds

    def slow_trial_done(self):
        return self.get_state_age() > five_minutes

    # state actions
    def on_enter_idle(self):
        self.pending_actions.clear()
        self.pending_actions.append(Actions.FAN_OFF)

    def on_enter_slow_ex_roof(self):
        self.pending_actions.clear()
        self.pending_actions.append(Actions.VALVES_EXTRACT_ROOF)
        self.pending_actions.append(Actions.FAN_LOW)

    def on_enter_slow_ex_lvrm(self):
        self.pending_actions.clear()
        self.pending_actions.append(Actions.VALVES_EXTRACT_LVRM)
        self.pending_actions.append(Actions.FAN_LOW)

    def on_enter_fast_ex_roof(self):
        self.pending_actions.clear()
        self.pending_actions.append(Actions.VALVES_EXTRACT_ROOF)
        self.pending_actions.append(Actions.FAN_HIGH)

    def on_enter_fast_ex_lvrm(self):
        self.pending_actions.clear()
        self.pending_actions.append(Actions.VALVES_EXTRACT_LVRM)
        self.pending_actions.append(Actions.FAN_HIGH)
