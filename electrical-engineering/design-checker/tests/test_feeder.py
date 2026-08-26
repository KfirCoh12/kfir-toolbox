import unittest

from src.cable import CableAmpacityInput
from src.feeder import FeederInput, check_feeder


class FeederCheckerTests(unittest.TestCase):
    def _cable(self, **overrides):
        values = dict(
            material="copper", cross_section_mm2=95, insulation="xlpe_epr",
            loaded_conductors=3, installation_method="E", environment="air",
            ambient_temperature_c=30, grouped_circuits=1,
            grouping_arrangement=None, parallel_runs=1,
            equal_current_sharing_confirmed=None, thdi_percent=0, neutral_loaded=False,
        )
        values.update(overrides)
        return CableAmpacityInput(**values)

    def _feeder(self, **overrides):
        values = dict(
            load_type="kw", load_value=97, voltage_v=400, phase="three",
            power_factor=0.9, demand_factor=1.0, breaker_in_a=200,
            cable=self._cable(),
        )
        values.update(overrides)
        return FeederInput(**values)

    def test_numerical_success_stays_not_verified_until_breaker_rule_is_verified(self):
        r = check_feeder(self._feeder())
        self.assertEqual(r.breaker.comparison, "PASS")
        self.assertEqual(r.ampacity_comparison.comparison, "PASS")
        self.assertEqual(r.ampacity.iz_a, 298.0)
        self.assertEqual(r.overall_outcome, "NOT VERIFIED")
        self.assertIn("breaker protection rule/current IEC basis", r.missing_or_unverified)

    def test_breaker_failure_controls_overall_outcome(self):
        r = check_feeder(self._feeder(breaker_in_a=100))
        self.assertEqual(r.breaker.comparison, "FAIL")
        self.assertEqual(r.overall_outcome, "FAIL")

    def test_ampacity_failure_controls_overall_outcome(self):
        r = check_feeder(self._feeder(load_value=190, breaker_in_a=400))
        self.assertEqual(r.ampacity_comparison.comparison, "FAIL")
        self.assertEqual(r.overall_outcome, "FAIL")

    def test_unsupported_cable_returns_not_verified_not_fake_pass(self):
        r = check_feeder(self._feeder(cable=self._cable(insulation="other")))
        self.assertEqual(r.ampacity_comparison.comparison, "NOT VERIFIED")
        self.assertEqual(r.overall_outcome, "NOT VERIFIED")

    def test_voltage_drop_with_explicit_limit_does_not_hide_breaker_gap(self):
        r = check_feeder(self._feeder(
            length_m=100, voltage_drop_cross_section_mm2=95,
            voltage_drop_material="copper", permitted_voltage_drop_percent=5.0,
            voltage_drop_limit_source="project criterion", allow_annex_g_defaults=True,
        ))
        self.assertIsNotNone(r.voltage_drop)
        self.assertIn(r.voltage_drop.comparison, ("PASS", "FAIL"))
        if r.voltage_drop.comparison == "PASS":
            self.assertEqual(r.overall_outcome, "NOT VERIFIED")

    def test_missing_breaker_is_not_verified(self):
        r = check_feeder(self._feeder(breaker_in_a=None))
        self.assertEqual(r.overall_outcome, "NOT VERIFIED")
        self.assertIn("breaker_in_a", r.missing_or_unverified)

    def test_undersized_connection_fails_existing_supply(self):
        r = check_feeder(self._feeder(connection_option_id="industrial_125a_3ph"))
        self.assertEqual(r.connection.comparison, "FAIL")
        self.assertEqual(r.overall_outcome, "FAIL")

    def test_connection_can_pass_numerically_but_remains_standards_incomplete(self):
        r = check_feeder(self._feeder(load_value=30, breaker_in_a=63, connection_option_id="industrial_63a_3ph"))
        self.assertEqual(r.connection.comparison, "PASS")
        self.assertEqual(r.connection.rating_a, 63.0)
        self.assertIn("connection product/standard basis", r.missing_or_unverified)
        self.assertEqual(r.overall_outcome, "NOT VERIFIED")

    def test_wrong_phase_connection_fails(self):
        r = check_feeder(self._feeder(load_value=5, breaker_in_a=16, connection_option_id="general_socket_16a_1ph"))
        self.assertEqual(r.connection.comparison, "FAIL")
        self.assertEqual(r.overall_outcome, "FAIL")


if __name__ == "__main__": unittest.main()
