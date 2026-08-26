import unittest

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.max_load import MaxLoadInput, calculate_max_load

class MaxLoadTests(unittest.TestCase):
    def _generic_95(self):
        cable=CableAmpacityInput(material="copper",cross_section_mm2=95,insulation="xlpe_epr",loaded_conductors=3,installation_method="E",environment="air",ambient_temperature_c=30,grouped_circuits=1,grouping_arrangement=None,parallel_runs=1,thdi_percent=0,neutral_loaded=False)
        return RoutedAmpacityInput(source_kind="iec_generic",generic=cable)

    def test_breaker_can_be_limiting_constraint(self):
        r=calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,breaker_in_a=63,ampacity_route=self._generic_95()))
        self.assertEqual(r.status,"RESULT")
        self.assertEqual(r.limiting_constraint,"breaker")
        self.assertAlmostEqual(r.max_current_a,63.0)
        self.assertGreater(r.max_kw,39.0)
        self.assertLess(r.max_kw,40.0)

    def test_cable_can_be_limiting_constraint(self):
        r=calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,breaker_in_a=400,ampacity_route=self._generic_95()))
        self.assertEqual(r.limiting_constraint,"cable ampacity")
        self.assertAlmostEqual(r.max_current_a,298.0)

    def test_connection_rating_participates_in_minimum(self):
        r=calculate_max_load(MaxLoadInput(voltage_v=230,phase="single",power_factor=1.0,breaker_in_a=25,connection_rating_a=16))
        self.assertEqual(r.limiting_constraint,"connection/outlet")
        self.assertAlmostEqual(r.max_kw,3.68,places=2)

    def test_voltage_drop_can_be_limiting_constraint(self):
        r=calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,breaker_in_a=200,ampacity_route=self._generic_95(),length_m=500,voltage_drop_cross_section_mm2=95,voltage_drop_material="copper",permitted_voltage_drop_percent=5,voltage_drop_limit_source="Project criterion",allow_annex_g_defaults=True))
        self.assertEqual(r.status,"RESULT")
        self.assertEqual(r.limiting_constraint,"voltage drop")
        self.assertLess(r.max_current_a,200)

    def test_missing_constraints_is_not_verified(self):
        r=calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertIsNone(r.max_kw)

    def test_unsupported_ampacity_does_not_become_fake_limit(self):
        bad=CableAmpacityInput(material="copper",cross_section_mm2=50,insulation="xlpe_epr",loaded_conductors=3,installation_method="E",environment="air",ambient_temperature_c=30,grouped_circuits=1,grouping_arrangement=None,parallel_runs=1,thdi_percent=0,neutral_loaded=False)
        r=calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,ampacity_route=RoutedAmpacityInput(source_kind="iec_generic",generic=bad)))
        self.assertEqual(r.status,"NOT VERIFIED")
        self.assertIsNone(r.max_current_a)

if __name__=="__main__": unittest.main()
