import unittest

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.max_load import MaxLoadInput, calculate_max_load


class CapacityCoverageTests(unittest.TestCase):
    def _cable_route(self):
        cable = CableAmpacityInput(
            material="copper", cross_section_mm2=95, insulation="xlpe_epr",
            loaded_conductors=3, installation_method="E", environment="air",
            ambient_temperature_c=30, grouped_circuits=1,
            grouping_arrangement=None, parallel_runs=1,
            thdi_percent=0, neutral_loaded=False,
        )
        return RoutedAmpacityInput(source_kind="iec_generic", generic=cable)

    def test_breaker_only_result_is_explicitly_partial(self):
        r = calculate_max_load(MaxLoadInput(
            voltage_v=400, phase="three", power_factor=0.9, breaker_in_a=63,
        ))
        self.assertEqual(r.status, "RESULT")
        self.assertEqual(r.coverage_status, "PARTIAL CORE COVERAGE")
        self.assertIn("Cable ampacity was not provided or checked.", r.missing_core_checks)
        self.assertIn("Outlet / connection rating was not provided.", r.missing_core_checks)

    def test_all_three_core_constraints_give_full_core_coverage(self):
        r = calculate_max_load(MaxLoadInput(
            voltage_v=400, phase="three", power_factor=0.9,
            breaker_in_a=63,
            connection_option_id="industrial_63a_3ph",
            ampacity_route=self._cable_route(),
        ))
        self.assertEqual(r.status, "RESULT")
        self.assertEqual(r.coverage_status, "FULL CORE COVERAGE")
        self.assertEqual(r.missing_core_checks, ())

    def test_fixed_connection_does_not_fake_a_complete_numeric_ceiling(self):
        r = calculate_max_load(MaxLoadInput(
            voltage_v=400, phase="three", power_factor=0.9,
            breaker_in_a=63,
            connection_option_id="fixed_connection_3ph",
            ampacity_route=self._cable_route(),
        ))
        self.assertEqual(r.status, "RESULT")
        self.assertEqual(r.coverage_status, "PARTIAL CORE COVERAGE")
        self.assertTrue(any("fixed connection" in x.lower() for x in r.missing_core_checks))

    def test_no_constraint_reports_no_usable_constraint(self):
        r = calculate_max_load(MaxLoadInput(
            voltage_v=400, phase="three", power_factor=0.9,
        ))
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertEqual(r.coverage_status, "NO USABLE CONSTRAINT")
        self.assertGreaterEqual(len(r.missing_core_checks), 3)


if __name__ == "__main__":
    unittest.main()
