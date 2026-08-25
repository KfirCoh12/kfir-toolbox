import unittest
from src.ampacity_router import RoutedAmpacityInput
from src.feeder import FeederInput, check_feeder

class ManufacturerFeederRouteTests(unittest.TestCase):
    def base(self, route):
        return FeederInput(load_type="kw",load_value=90,voltage_v=400,phase="three",power_factor=0.9,breaker_in_a=200,ampacity_route=route)

    def test_supported_single_run_reaches_feeder_comparison(self):
        r=check_feeder(self.base(RoutedAmpacityInput(source_kind="manufacturer_nhxh_fe180_e90",construction="3x95+50",ambient_temperature_c=30,grouped_circuits=1,parallel_runs=1)))
        self.assertEqual(r.ampacity.iz_a,305.0)
        self.assertEqual(r.ampacity_comparison.comparison,"PASS")
        self.assertEqual(r.ampacity.source_metadata["source_kind"],"manufacturer")
        self.assertEqual(r.overall_outcome,"NOT VERIFIED")

    def test_parallel_manufacturer_case_stays_not_verified(self):
        r=check_feeder(self.base(RoutedAmpacityInput(source_kind="manufacturer_nhxh_fe180_e90",construction="3x95+50",ambient_temperature_c=30,grouped_circuits=1,parallel_runs=2,equal_current_sharing_confirmed=True)))
        self.assertIsNone(r.ampacity.iz_a)
        self.assertEqual(r.ampacity_comparison.comparison,"NOT VERIFIED")
        self.assertIn("parallel/grouped manufacturer ampacity correction is not yet integrated",r.missing_or_unverified)

if __name__=="__main__": unittest.main()
