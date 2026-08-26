import unittest
from src.circuit_selector import CircuitSelectionInput, select_circuit, select_material_options

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

    def test_single_phase_is_explicitly_not_yet_supported_for_auto_cable_selection(self):
        r=select_circuit(CircuitSelectionInput(load_type="kw",load_value=5,voltage_v=230,phase="single",power_factor=0.9))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertIsNone(r.suggested_cable_mm2)

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

if __name__=="__main__": unittest.main()
