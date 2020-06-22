import datetime
from enum import IntEnum

from . import hardware_state_machine


# Used for comparison so must be in order
class BenefitScores(IntEnum):
    terrible = 0
    bad = 1
    ok = 2
    good = 3
    ideal = 4


class EventSelector:
    target_humidity = 30
    max_rh = 55
    temp_hysteresis = 1
    min_temp_error_to_activate = 1
    min_temp_advantage = 2
    terrible_roof_error = -5
    humidity_hysteresis = 10
    min_humidity_advantage = 5
    beginning_bed_time = 17
    getting_up_time = 7
    quiet_fan_start = 19
    quiet_fan_end = 8
    high_bedroom_error = 3

    def select_event(self, enabled, fresh_data, climate_state, force_hard_flush, target_temperature):
        if fresh_data:
            roof_temp_diff = climate_state.roof_data.get_temp() - target_temperature
            lvrm_temp_diff = climate_state.lvrm_data.get_temp() - target_temperature
            bdrm_temp_diff = climate_state.bdrm_data.get_temp() - target_temperature

            roof_temp_score = self.get_roof_temp_score(roof_temp_diff, lvrm_temp_diff, bdrm_temp_diff)
            lvrm_temp_score = self.get_lvrm_temp_score(lvrm_temp_diff, bdrm_temp_diff)
            roof_humidity_score = self.get_roof_humidity_score(climate_state)
            roof_worst = self.is_roof_worst_source(roof_temp_diff, lvrm_temp_diff, bdrm_temp_diff)

        if not enabled:
            event_str = hardware_state_machine.force_idle_str
        elif force_hard_flush:
            event_str = hardware_state_machine.hard_flush_str
        elif not fresh_data:
            event_str = hardware_state_machine.lvrm_worst_str
        elif roof_temp_score == BenefitScores.ideal:
            event_str = hardware_state_machine.roof_ideal_str
        elif roof_temp_score == BenefitScores.good:
            event_str = hardware_state_machine.roof_good__str
        elif roof_temp_score == BenefitScores.ok:
            event_str = hardware_state_machine.roof_go_on_str
        elif lvrm_temp_score == BenefitScores.ideal:
            event_str = hardware_state_machine.lvrm_ideal_str
        elif lvrm_temp_score == BenefitScores.good:
            event_str = hardware_state_machine.lvrm_good__str
        elif lvrm_temp_score == BenefitScores.ok:
            event_str = hardware_state_machine.lvrm_go_on_str
        elif roof_humidity_score == BenefitScores.ideal and roof_temp_score != BenefitScores.terrible:
            event_str = hardware_state_machine.roof_ideal_str
        elif roof_humidity_score == BenefitScores.ok and roof_temp_score != BenefitScores.terrible:
            event_str = hardware_state_machine.roof_go_on_str
        elif roof_worst:
            event_str = hardware_state_machine.roof_worst_str
        else:
            event_str = hardware_state_machine.lvrm_worst_str
        return event_str

    def _temper_score_for_quiet_fan(func):
        def wrapper(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            if self._want_quiet_fan() and r == BenefitScores.ideal:
                r = BenefitScores.good
            return r
        return wrapper

    @_temper_score_for_quiet_fan
    def get_roof_temp_score(self, roof_temp_diff, lvrm_temp_diff, bdrm_temp_diff):
        # should roof be extracted to living and bed rooms?
        if self._bedroom_temps_matter():
            house_error = (lvrm_temp_diff + bdrm_temp_diff) / 2
        else:
            house_error = lvrm_temp_diff
        if house_error < 0:
            roof_advantage = roof_temp_diff - house_error
        else:
            roof_advantage = house_error - roof_temp_diff
        return self._temp_advantage_to_score(roof_advantage, house_error)

    @_temper_score_for_quiet_fan
    def get_lvrm_temp_score(self, lvrm_temp_diff, bdrm_temp_diff):
        # Should living room be extracted to bedrooms?
        score = BenefitScores.bad
        if self._bedroom_temps_matter():
            if bdrm_temp_diff < 0:
                lvrm_advantage = lvrm_temp_diff - bdrm_temp_diff
            else:
                lvrm_advantage = bdrm_temp_diff - lvrm_temp_diff
            score = self._temp_advantage_to_score(lvrm_advantage, bdrm_temp_diff)
        return score

    @_temper_score_for_quiet_fan
    def get_roof_humidity_score(self, climate_state):
        roof_rh = climate_state.roof_data.get_humidity()
        lvrm_rh = climate_state.lvrm_data.get_humidity()
        bdrm_rh = climate_state.bdrm_data.get_humidity()
        house_rh = (lvrm_rh + bdrm_rh) / 2
        roof_advantage = house_rh - roof_rh
        score = BenefitScores.bad
        if house_rh > self.max_rh:
            if roof_advantage > self.humidity_hysteresis:
                score = BenefitScores.ideal
            elif roof_advantage > self.min_humidity_advantage:
                score = BenefitScores.ok
        return score

    def is_roof_worst_source(self, roof_temp_diff, lvrm_temp_diff, bdrm_temp_diff):
        # no good options but where should flush come from?
        roof_is_worst = False
        if self._bedroom_temps_matter():
            if abs(bdrm_temp_diff) > self.high_bedroom_error:
                if bdrm_temp_diff < 0:
                    roof_advantage = roof_temp_diff - bdrm_temp_diff
                    lvrm_advantage = lvrm_temp_diff - bdrm_temp_diff
                else:
                    roof_advantage = bdrm_temp_diff - roof_temp_diff
                    lvrm_advantage = bdrm_temp_diff - lvrm_temp_diff
                roof_is_worst = lvrm_advantage > roof_advantage
        return roof_is_worst

    def _temp_advantage_to_score(self, temp_advantage, error):
        if abs(error) < self.min_temp_error_to_activate:
            max_score = BenefitScores.bad
        elif abs(error) < self.min_temp_error_to_activate + self.temp_hysteresis:
            max_score = BenefitScores.ok
        else:
            max_score = BenefitScores.ideal

        if temp_advantage > self.min_temp_advantage + self.temp_hysteresis:
            score = BenefitScores.ideal
        elif temp_advantage > self.min_temp_advantage:
            score = BenefitScores.ok
        elif temp_advantage > self.terrible_roof_error:
            score = BenefitScores.bad
        else:
            score = BenefitScores.terrible

        return min(score, max_score)

    def _bedroom_temps_matter(self):
        current_hour = datetime.datetime.now().hour
        return current_hour >= self.beginning_bed_time or current_hour <= self.getting_up_time

    def _want_quiet_fan(self):
        current_hour = datetime.datetime.now().hour
        return current_hour >= self.quiet_fan_start or current_hour <= self.quiet_fan_end
