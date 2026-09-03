import unittest
from src.circuit_selector import CircuitSelectionInput, assess_installation_support, explain_circuit_selection, select_circuit, select_material_options

class CircuitSelectorTests(unittest.TestCase):
    def test_selects_first_supported_cable_that_carries_breaker(self):
        r=select_circuit(CircuitSelectionInput(load_type="kw",load_value=30,voltage_v=400,phase="three",power_factor=0.9,demand_factor=0.8))
        self.assertEqual(r.status,"SUGGESTION")
        self.assertEqual(r.suggested_breaker_a,40.0)
        self.assertEqual(r.suggested_cable_mm2,10.0)
        self.assertGreaterEqual(r.cable_iz_a,r.suggested_breaker_a)
        self.assertTrue(any("60364-4-43" in x for x in r.limitations))

    def test_skips_ampacity_candidate_when_grouping_reduces_iz_below_breaker(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=70,voltage_v=400,phase="three",power_factor=0.9,grouped_circuits=2,grouping_arrangement="bunched"))
        self.assertEqual(r.suggested_breaker_a,80.0)
        self.assertEqual(r.suggested_cable_mm2,25.0)
        self.assertTrue(any("10 mm²" in x for x in r.rejected_candidates))

    def test_voltage_drop_can_force_larger_cable(self):
        base=select_circuit(CircuitSelectionInput(load_type="a",load_value=60,voltage_v=400,phase="three",power_factor=0.9,length_m=200,permitted_voltage_drop_percent=5.0,voltage_drop_limit_source="Project criterion",allow_annex_g_defaults=True))
        self.assertEqual(base.status,"SUGGESTION")
        self.assertGreater(base.suggested_cable_mm2,10.0)
        self.assertEqual(base.voltage_drop.comparison,"PASS")

    def test_single_phase_uses_two_loaded_conductor_method_e_dataset(self):
        r=select_circuit(CircuitSelectionInput(load_type="kw",load_value=5,voltage_v=230,phase="single",power_factor=0.9))
        self.assertEqual(r.status,"SUGGESTION")
        self.assertEqual(r.suggested_breaker_a,25.0)
        self.assertEqual(r.suggested_cable_mm2,1.5)
        self.assertEqual(r.cable_iz_a,26.0)
        self.assertTrue(any("two loaded conductors" in x.lower() for x in r.trace))
        self.assertTrue(any("harmonic-rich neutral loading" in x for x in r.limitations))

    def test_does_not_invent_size_outside_dataset(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=600,voltage_v=400,phase="three",power_factor=0.9))
        self.assertEqual(r.status,"NO SUPPORTED SOLUTION")
        self.assertIsNone(r.suggested_cable_mm2)

    def test_material_options_are_independently_calculated(self):
        options=select_material_options(CircuitSelectionInput(load_type="kw",load_value=30,voltage_v=400,phase="three",power_factor=0.9,demand_factor=0.8,length_m=50,permitted_voltage_drop_percent=5.0,voltage_drop_limit_source="Project criterion",allow_annex_g_defaults=True))
        self.assertEqual(options.copper.suggested_cable_mm2,10.0)
        self.assertEqual(options.aluminium.suggested_cable_mm2,10.0)
        self.assertGreater(options.copper.cable_iz_a,options.aluminium.cable_iz_a)
        self.assertLess(options.copper.voltage_drop.voltage_drop_percent,options.aluminium.voltage_drop.voltage_drop_percent)

    def test_explanation_traces_breaker_cable_and_connection_choices(self):
        r=select_circuit(CircuitSelectionInput(load_type="kw",load_value=30,voltage_v=400,phase="three",power_factor=0.9,demand_factor=0.8))
        e=explain_circuit_selection(r)
        self.assertIn("40 A", e.breaker_reason)
        self.assertIn("Ib", e.breaker_reason)
        self.assertIn("10 mm²", e.cable_reason)
        self.assertIn("Iz", e.cable_reason)
        self.assertIn("63 A", e.connection_reason)
        self.assertIn("Ib", e.summary)

    def test_explanation_preserves_reasons_smaller_cables_were_rejected(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=60,voltage_v=400,phase="three",power_factor=0.9,length_m=200,permitted_voltage_drop_percent=5.0,voltage_drop_limit_source="Project criterion",allow_annex_g_defaults=True))
        e=explain_circuit_selection(r)
        self.assertTrue(e.why_not_smaller)
        self.assertTrue(any("voltage drop" in x.lower() or "Iz" in x for x in e.why_not_smaller))
        self.assertIn("passes", e.voltage_drop_reason.lower())

    def test_explanation_does_not_claim_protection_compliance(self):
        r=select_circuit(CircuitSelectionInput(load_type="kw",load_value=30,voltage_v=400,phase="three",power_factor=0.9,demand_factor=0.8))
        e=explain_circuit_selection(r)
        combined=" ".join((e.summary,e.breaker_reason,e.cable_reason,e.connection_reason,e.voltage_drop_reason or ""))
        self.assertNotIn("compliant", combined.lower())
        self.assertNotIn("verified protection", combined.lower())

    def test_unsupported_ambient_condition_is_not_misreported_as_no_solution(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=60,voltage_v=400,phase="three",power_factor=0.9,ambient_temperature_c=55))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertIsNone(r.suggested_cable_mm2)
        self.assertTrue(any("ambient temperature" in x.lower() for x in r.limitations))
        self.assertEqual(r.rejected_candidates, tuple())

    def test_unsupported_group_count_is_reported_with_reason(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=60,voltage_v=400,phase="three",power_factor=0.9,grouped_circuits=10,grouping_arrangement="bunched"))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertTrue(any("group count" in x.lower() for x in r.limitations))
        self.assertEqual(r.rejected_candidates, tuple())

    def test_supported_but_inadequate_dataset_remains_no_supported_solution(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=600,voltage_v=400,phase="three",power_factor=0.9))
        self.assertEqual(r.status,"NO SUPPORTED SOLUTION")
        self.assertTrue(any("all requested installation conditions were supported" in x.lower() for x in r.trace))

    def test_parallel_runs_require_explicit_current_sharing_confirmation(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=180,voltage_v=400,phase="three",power_factor=0.9,parallel_runs=2,grouped_circuits=2,grouping_arrangement="bunched"))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertIsNone(r.suggested_cable_mm2)
        self.assertTrue(any("explicit confirmation" in x for x in r.limitations))

    def test_parallel_runs_require_grouping_to_include_all_runs(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=180,voltage_v=400,phase="three",power_factor=0.9,parallel_runs=2,equal_current_sharing_confirmed=True,grouped_circuits=1))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertTrue(any("at least all parallel runs" in x for x in r.limitations))

    def test_confirmed_parallel_runs_can_form_supported_aggregate_ampacity(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=180,voltage_v=400,phase="three",power_factor=0.9,parallel_runs=2,equal_current_sharing_confirmed=True,grouped_circuits=2,grouping_arrangement="bunched"))
        self.assertEqual(r.status,"SUGGESTION")
        self.assertEqual(r.suggested_parallel_runs,2)
        self.assertEqual(r.suggested_cable_mm2,25.0)
        self.assertGreaterEqual(r.cable_iz_a,r.suggested_breaker_a)
        explanation=explain_circuit_selection(r)
        self.assertIn("2 × 25 mm²",explanation.summary)
        self.assertIn("aggregate Iz",explanation.cable_reason)

    def test_parallel_voltage_drop_uses_equal_shared_current(self):
        r=select_circuit(CircuitSelectionInput(load_type="a",load_value=180,voltage_v=400,phase="three",power_factor=0.9,parallel_runs=2,equal_current_sharing_confirmed=True,grouped_circuits=2,grouping_arrangement="bunched",length_m=50,permitted_voltage_drop_percent=5.0,voltage_drop_limit_source="Project criterion",allow_annex_g_defaults=True))
        self.assertEqual(r.status,"SUGGESTION")
        self.assertTrue(any("Voltage-drop current per run" in x for x in r.trace))
        self.assertTrue(any("identical run" in x for x in r.limitations))

    def test_installation_support_preflight_reports_supported_conditions(self):
        a = assess_installation_support(CircuitSelectionInput(
            load_type="kw", load_value=30, voltage_v=400, phase="three", power_factor=0.9,
            ambient_temperature_c=30, grouped_circuits=1,
        ))
        self.assertEqual(a.status, "SUPPORTED")
        self.assertIn("IEC reference Method E", a.supported_conditions)
        self.assertIn("ambient air temperature 30 °C", a.supported_conditions)
        self.assertEqual(a.missing_or_unsupported, tuple())

    def test_single_phase_preflight_reports_two_loaded_conductor_basis(self):
        a = assess_installation_support(CircuitSelectionInput(
            load_type="kw", load_value=5, voltage_v=230, phase="single", power_factor=0.9,
            ambient_temperature_c=30, grouped_circuits=1,
        ))
        self.assertEqual(a.status, "SUPPORTED")
        self.assertIn("two loaded conductors (phase + neutral)", a.supported_conditions)
        self.assertEqual(a.missing_or_unsupported, tuple())

    def test_installation_support_preflight_reports_unsupported_reason_before_iteration(self):
        data = CircuitSelectionInput(
            load_type="kw", load_value=30, voltage_v=400, phase="three", power_factor=0.9,
            ambient_temperature_c=55, grouped_circuits=1,
        )
        a = assess_installation_support(data)
        self.assertEqual(a.status, "NOT VERIFIED")
        self.assertTrue(any("ambient temperature" in x for x in a.missing_or_unsupported))
        r = select_circuit(data)
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertEqual(r.rejected_candidates, tuple())
        self.assertTrue(any("Installation support preflight = NOT VERIFIED" in x for x in r.trace))

    def test_installation_support_preflight_does_not_treat_parallel_guard_as_supported(self):
        a = assess_installation_support(CircuitSelectionInput(
            load_type="a", load_value=100, voltage_v=400, phase="three", power_factor=0.9,
            parallel_runs=2, equal_current_sharing_confirmed=False, grouped_circuits=2, grouping_arrangement="bunched",
        ))
        self.assertEqual(a.status, "NOT VERIFIED")
        self.assertTrue(any("parallel runs require explicit confirmation" in x for x in a.missing_or_unsupported))

if __name__=="__main__": unittest.main()
