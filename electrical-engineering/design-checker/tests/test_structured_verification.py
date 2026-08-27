import unittest

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.circuit_selector import CircuitSelectionInput, select_circuit
from src.max_load import MaxLoadInput, calculate_max_load
from src.verification import (
    summarize_circuit_selection_verification,
    summarize_max_load_verification,
)


class StructuredVerificationTests(unittest.TestCase):
    def _generic_95(self):
        cable = CableAmpacityInput(
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
        return RoutedAmpacityInput(source_kind="iec_generic", generic=cable)

    def test_supported_forward_selection_has_machine_readable_scope_and_limitations(self):
        result = select_circuit(CircuitSelectionInput(
            load_type="kw",
            load_value=30,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            demand_factor=0.8,
        ))
        summary = summarize_circuit_selection_verification(result)
        self.assertEqual(summary.scope_status, "SUPPORTED_SCOPE")
        codes = {issue.code for issue in summary.issues}
        self.assertIn("protection_standard_not_implemented", codes)
        self.assertIn("connection_configuration_not_verified", codes)
        self.assertFalse(any(issue.code == "automatic_selection_not_verified" for issue in summary.issues))

    def test_single_phase_forward_result_is_partial_scope_with_cable_dataset_blocker(self):
        result = select_circuit(CircuitSelectionInput(
            load_type="kw",
            load_value=5,
            voltage_v=230,
            phase="single",
            power_factor=0.9,
        ))
        summary = summarize_circuit_selection_verification(result)
        self.assertEqual(summary.scope_status, "PARTIAL_SCOPE")
        blockers = {issue.code for issue in summary.blocking_issues}
        self.assertIn("cable_dataset_phase_unsupported", blockers)

    def test_parallel_sharing_guard_has_stable_issue_code(self):
        result = select_circuit(CircuitSelectionInput(
            load_type="a",
            load_value=180,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            parallel_runs=2,
            grouped_circuits=2,
            grouping_arrangement="bunched",
        ))
        summary = summarize_circuit_selection_verification(result)
        self.assertEqual(summary.scope_status, "PARTIAL_SCOPE")
        blockers = {issue.code for issue in summary.blocking_issues}
        self.assertIn("parallel_current_sharing_not_confirmed", blockers)

    def test_supported_but_inadequate_dataset_is_not_mislabeled_not_verified(self):
        result = select_circuit(CircuitSelectionInput(
            load_type="a",
            load_value=600,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
        ))
        summary = summarize_circuit_selection_verification(result)
        self.assertEqual(summary.scope_status, "SUPPORTED_SCOPE")
        blockers = {issue.code for issue in summary.blocking_issues}
        self.assertIn("no_supported_solution", blockers)

    def test_reverse_capacity_partial_coverage_exposes_missing_component_codes(self):
        result = calculate_max_load(MaxLoadInput(
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            breaker_in_a=63,
        ))
        summary = summarize_max_load_verification(result)
        self.assertEqual(summary.scope_status, "PARTIAL_SCOPE")
        blockers = {issue.code for issue in summary.blocking_issues}
        self.assertIn("missing_connection_check", blockers)
        self.assertIn("missing_cable_check", blockers)
        self.assertNotIn("missing_breaker_check", blockers)

    def test_reverse_capacity_full_core_coverage_is_supported_scope_not_compliance_claim(self):
        result = calculate_max_load(MaxLoadInput(
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            breaker_in_a=200,
            connection_rating_a=250,
            ampacity_route=self._generic_95(),
        ))
        summary = summarize_max_load_verification(result)
        self.assertEqual(summary.scope_status, "SUPPORTED_SCOPE")
        codes = {issue.code for issue in summary.issues}
        self.assertIn("protection_standard_not_implemented", codes)
        self.assertIn("connection_configuration_not_verified", codes)

    def test_reverse_capacity_without_any_usable_constraint_is_not_verified(self):
        result = calculate_max_load(MaxLoadInput(
            voltage_v=400,
            phase="three",
            power_factor=0.9,
        ))
        summary = summarize_max_load_verification(result)
        self.assertEqual(summary.scope_status, "NOT_VERIFIED")
        blockers = {issue.code for issue in summary.blocking_issues}
        self.assertIn("no_usable_constraint", blockers)
        self.assertIn("missing_breaker_check", blockers)
        self.assertIn("missing_connection_check", blockers)
        self.assertIn("missing_cable_check", blockers)


if __name__ == "__main__":
    unittest.main()
