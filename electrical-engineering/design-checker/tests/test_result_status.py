import unittest

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.feeder import FeederInput, check_feeder
from src.result_status import summarize_feeder_result


class ResultStatusTests(unittest.TestCase):
    def _generic_cable(self):
        return CableAmpacityInput(
            material="copper",
            cross_section_mm2=95,
            insulation="xlpe_epr",
            loaded_conductors=3,
            installation_method="E",
            environment="air",
            ambient_temperature_c=30,
            grouped_circuits=1,
            grouping_arrangement=None,
            parallel_runs=1,
            equal_current_sharing_confirmed=None,
            thdi_percent=0,
            neutral_loaded=False,
        )

    def _feeder(self, **overrides):
        cable = self._generic_cable()
        values = dict(
            load_type="kw",
            load_value=97,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            demand_factor=1.0,
            breaker_in_a=200,
            cable=cable,
            ampacity_route=RoutedAmpacityInput(source_kind="iec_generic", generic=cable),
        )
        values.update(overrides)
        return FeederInput(**values)

    def test_numerical_pass_can_be_engineering_pass_while_standards_incomplete(self):
        r = check_feeder(self._feeder())
        s = summarize_feeder_result(r, voltage_drop_requested=False)
        self.assertEqual(s.engineering_status, "PASS")
        self.assertEqual(s.standards_status, "INCOMPLETE")
        self.assertEqual(s.primary_blocker, "breaker protection rule/current IEC basis")
        self.assertIn("IEC 60364-4-43", s.primary_message)

    def test_failed_breaker_controls_engineering_summary(self):
        r = check_feeder(self._feeder(breaker_in_a=100))
        s = summarize_feeder_result(r, voltage_drop_requested=False)
        self.assertEqual(s.engineering_status, "FAIL")
        self.assertEqual(s.standards_status, "INCOMPLETE")
        self.assertIn("engineering checks failed", s.primary_message)

    def test_requested_voltage_drop_without_check_is_engineering_incomplete(self):
        r = check_feeder(self._feeder(length_m=100))
        s = summarize_feeder_result(r, voltage_drop_requested=True)
        self.assertEqual(s.engineering_status, "INCOMPLETE")
        self.assertEqual(s.standards_status, "INCOMPLETE")

    def test_open_item_count_matches_backend(self):
        r = check_feeder(self._feeder())
        s = summarize_feeder_result(r, voltage_drop_requested=False)
        self.assertEqual(s.open_item_count, len(r.missing_or_unverified))

    def test_summary_exposes_actionable_headroom_details(self):
        r = check_feeder(self._feeder(
            length_m=100, voltage_drop_cross_section_mm2=95, voltage_drop_material="copper",
            permitted_voltage_drop_percent=5.0, voltage_drop_limit_source="project criterion",
            allow_annex_g_defaults=True,
        ))
        s = summarize_feeder_result(r, voltage_drop_requested=True)
        self.assertIn("numerical headroom", s.breaker_detail)
        self.assertIn("ampacity headroom", s.cable_detail)
        self.assertIn("percentage points remaining", s.voltage_drop_detail)

    def test_failed_breaker_detail_states_deficit_without_guessing_replacement(self):
        r = check_feeder(self._feeder(breaker_in_a=100))
        s = summarize_feeder_result(r, voltage_drop_requested=False)
        self.assertIn("Ib exceeds In", s.breaker_detail)
        self.assertIn("revise", s.breaker_detail)
        self.assertNotIn("125 A", s.breaker_detail)

    def test_voltage_drop_without_limit_is_explicit(self):
        r = check_feeder(self._feeder(
            length_m=100, voltage_drop_cross_section_mm2=95, voltage_drop_material="copper",
            allow_annex_g_defaults=True,
        ))
        s = summarize_feeder_result(r, voltage_drop_requested=True)
        self.assertIn("no verified permitted limit", s.voltage_drop_detail)


if __name__ == "__main__":
    unittest.main()
