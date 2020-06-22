import unittest
from unittest.mock import MagicMock

from controller import controller
from common.common import *


class TestController(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._controller = controller.Controller()
        cls.perform_action = MagicMock(return_value=None)

    def set_state_age(self, age=60):
        self._controller.hardware_state.get_state_age = MagicMock(return_value=age)

    def set_fresh_data(self, fresh):
        self._controller.climate_state.is_fresh = MagicMock(return_value=fresh)

    def set_bedroom_temps_matter(self, matter):
        self._controller.event_selector._bedroom_temps_matter = MagicMock(return_value=matter)
    
    def set_want_quiet_fan(self, quiet_fan):
        self._controller.event_selector._want_quiet_fan = MagicMock(return_value=quiet_fan)

    def test_controller_01(self):
        # roof towards target so ex roof
        self.set_state_age(0)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self.set_want_quiet_fan(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_02(self):
        # still ex roof slow as no time has passed
        self.set_state_age(0)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_03(self):
        # 5 mins passed so go faster
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_04(self):
        # stale data so back to idle
        self.set_state_age()
        self.set_fresh_data(False)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'17.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_05(self):
        # roof cooled down so back to idle
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'17.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_06(self):
        # no good option and flush not needed so do nothing
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'17.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_07(self):
        # wait longer period so flush from roof
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'17.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_08(self):
        # flush done so back to idle
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'17.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_09(self):
        # flush from roof as br not cold enough to extract from inside house even though lvrm warmer
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'15.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'16.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'17.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_10(self):
        # flush done so back to idle
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'15.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'16.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'17.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_11(self):
        # stay idle as flush not needed
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'13.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'14.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'15.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_12(self):
        # now take from lvrm as bedroom too cold
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'13.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'14.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'15.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_lvrm')

    def test_controller_13(self):
        # extract fast from living as ideal
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'14.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'15.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_lvrm')

    def test_controller_15(self):
        # back to idle as bed room temps no longer matter
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'14.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'15.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_16(self):
        # bdrm too hot start pulling from living
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_lvrm')

    def test_controller_17(self):
        # bdrm still too hot pull fast from living
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_lvrm')

    def test_controller_18(self):
        # back to idle as bdrm no longer matters
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_19(self):
        # no good option and no flush needed so remain idle
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_20(self):
        # no good option and flush needed so ex roof
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_21(self):
        # no good option and flush not finished so keep going
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_22(self):
        # no good option and flush not finished so keep going
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'27.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_23(self):
        # move from flush to fast as roof colder
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'25.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_24(self):
        # back to idle as lvrm good
        self.set_state_age()
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'23.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_25(self):
        # roof wet so don't pull
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 60.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'26.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_25b(self):
        # roof too hot so don't dry
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'30.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_26(self):
        # house wet so pull roof
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'26.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_27(self):
        # house still wet so pull roof fast
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'26.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_28(self):
        # house still wet but br temps over rule
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'26.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_29(self):
        # house still wet but br temps over rule
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'26.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_lvrm')
        
    def test_controller_30(self):
        # force hard flush in ui
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.request_flush()
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'30.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 56.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 56.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_31(self):
        # hard flush should still be enforced
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'30.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 50.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 50.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_32(self):
        # hard flush should be complete
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'30.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 50.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 50.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_33(self):
        # change target to use roof instead of slow_ex_lvrm
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        for _ in range(10):
            self._controller.increase_target_temp()
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'19.0 50.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'21.0 50.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_34(self):
        # disable should return to idle
        self.set_state_age(4000)
        self.set_fresh_data(True)
        self._controller.toggle_enable()
        for _ in range(10):
            self._controller.decrease_target_temp()
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'26.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'19.0 50.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'21.0 50.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_35(self):
        # while disabled even force flush should remain as idle
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.request_flush()
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'30.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'22.0 50.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'30.0 50.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_36(self):
        # force hard flush in ui after re-enabling
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(True)
        self._controller.toggle_enable()
        self._controller.request_flush()
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'30.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'19.0 50.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'19.0 50.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_37(self):
        # long time with no data, go back to idle
        self.set_state_age(6000)
        self.set_fresh_data(False)
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_38(self):
        # long time with no data but flush as selected in ui
        self.set_state_age(6000)
        self.set_fresh_data(False)
        self._controller.request_flush()
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'fast_ex_roof')

    def test_controller_38b(self):
        # long time with no data, go back to idle
        self.set_state_age(6000)
        self.set_fresh_data(False)
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_39(self):
        # roof towards target so ex roof
        self.set_state_age(0)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self.set_want_quiet_fan(True)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_40(self):
        # 5 mins passed but should stay slow as quiet fan time
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.0 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.0 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_41(self):
        # stay on as still inside activation hysteresis. Target is 20
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.5 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.5 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')

    def test_controller_42(self):
        # turn off as inside min error
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'19.5 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'19.5 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_43(self):
        # stay off as not enough error to exceed hysteresis reqs, even though same as 41
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'28.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'18.5 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'18.5 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')

    def test_controller_44(self):
        # error to exceeds hysteresis but insufficient advantage. stay off
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'20.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'17.5 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'17.5 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'idle')
    
    def test_controller_45(self):
        # sufficient advantage, turn on
        self.set_state_age(600)
        self.set_fresh_data(True)
        self.set_bedroom_temps_matter(False)
        self._controller.climate_state.process_update(Topic.ROOF_TEMP_HUM, b'21.0 30.0')
        self._controller.climate_state.process_update(Topic.LR_TEMP_HUM, b'17.5 30.0')
        self._controller.climate_state.process_update(Topic.BR_TEMP_HUM, b'17.5 30.0')
        self._controller.analyse_state()
        self.assertEqual(self._controller.hardware_state.state, 'slow_ex_roof')


if __name__ == '__main__':
    unittest.main()
