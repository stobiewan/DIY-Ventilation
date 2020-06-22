
sleep_period_seconds = 60


class Topic:
    BR_TEMP_HUM = 1
    LR_TEMP_HUM = 2
    ROOF_TEMP_HUM = 3
    SET_FAN = 4
    SET_VALVES = 5


class FanSpeeds:
    OFF = 1
    LOW = 2
    HIGH = 3


class ValveStates:
    extract_from_living = 1
    extract_from_roof = 2
    transitioning = 3
    unknown = 4
