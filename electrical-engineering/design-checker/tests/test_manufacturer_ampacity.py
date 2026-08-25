import unittest

from src.manufacturer_ampacity import get_nhxh_fe180_e90_air_30c


class ManufacturerAmpacityTests(unittest.TestCase):
    def test_exact_real_case_constructions_are_available(self):
        expected = {
            "3x95+50": 305.0,
            "3x120+70": 355.0,
            "5x25": 130.0,
            "5x10": 73.0,
        }
        for construction, ampacity in expected.items():
            with self.subTest(construction=construction):
                r = get_nhxh_fe180_e90_air_30c(construction)
                self.assertIsNotNone(r)
                self.assertEqual(r.current_capacity_air_a, ampacity)
                self.assertEqual(r.ambient_c, 30.0)
                self.assertEqual(r.conductor_material, "copper")

    def test_unknown_construction_is_not_interpolated(self):
        self.assertIsNone(get_nhxh_fe180_e90_air_30c("5x95"))

    def test_provenance_is_not_labelled_as_iec_ampacity(self):
        r = get_nhxh_fe180_e90_air_30c("3x95+50")
        self.assertIsNotNone(r)
        self.assertIn("manufacturer", r.ampacity_basis.lower())
        self.assertNotIn("IEC 60364 table", r.ampacity_basis)

    def test_e90_warning_is_preserved(self):
        r = get_nhxh_fe180_e90_air_30c("5x25")
        self.assertIsNotNone(r)
        self.assertIn("system", r.e90_note.lower())
        self.assertIn("installation", r.e90_note.lower())


if __name__ == "__main__":
    unittest.main()
