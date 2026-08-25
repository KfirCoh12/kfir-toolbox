import unittest

from src.ampacity_router import RoutedAmpacityInput, calculate_routed_ampacity


class AmpacityRouterTests(unittest.TestCase):
    def test_single_run_nhxh_exact_case_can_use_manufacturer_base_rating(self):
        r = calculate_routed_ampacity(RoutedAmpacityInput(
            source_kind="manufacturer_nhxh_fe180_e90",
            construction="3x95+50",
            ambient_temperature_c=30.0,
        ))
        self.assertEqual(r.iz_a, 305.0)
        self.assertIn("MANUFACTURER DATA VERIFIED", r.status)
        self.assertEqual(r.source_metadata["source_kind"], "manufacturer")

    def test_grouping_is_not_silently_borrowed_from_generic_iec_path(self):
        r = calculate_routed_ampacity(RoutedAmpacityInput(
            source_kind="manufacturer_nhxh_fe180_e90",
            construction="3x120+70",
            ambient_temperature_c=30.0,
            grouped_circuits=6,
            parallel_runs=6,
            equal_current_sharing_confirmed=True,
        ))
        self.assertIsNone(r.iz_a)
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertTrue(any("group" in x.lower() for x in r.missing_or_unsupported))

    def test_non_30c_manufacturer_case_stays_unverified_until_correction_source_exists(self):
        r = calculate_routed_ampacity(RoutedAmpacityInput(
            source_kind="manufacturer_nhxh_fe180_e90",
            construction="5x25",
            ambient_temperature_c=35.0,
        ))
        self.assertIsNone(r.iz_a)
        self.assertTrue(any("30" in x for x in r.missing_or_unsupported))

    def test_unknown_construction_is_not_interpolated(self):
        r = calculate_routed_ampacity(RoutedAmpacityInput(
            source_kind="manufacturer_nhxh_fe180_e90",
            construction="5x95",
            ambient_temperature_c=30.0,
        ))
        self.assertIsNone(r.iz_a)
        self.assertEqual(r.status, "NOT VERIFIED")


if __name__ == "__main__":
    unittest.main()
