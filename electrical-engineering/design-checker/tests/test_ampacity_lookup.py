import unittest

from src.cable import CableAmpacityInput, calculate_supported_iz


class AmpacityLookupTests(unittest.TestCase):
    def _base(self, **overrides):
        values = dict(
            material="copper",
            cross_section_mm2=95,
            insulation="xlpe_epr",
            loaded_conductors=3,
            installation_method="E",
            environment="air",
            ambient_temperature_c=30,
            grouped_circuits=1,
            parallel_runs=1,
            thdi_percent=0,
            neutral_loaded=False,
        )
        values.update(overrides)
        return CableAmpacityInput(**values)

    def test_copper_95_method_e_reference_condition(self):
        r = calculate_supported_iz(self._base())
        self.assertEqual(r.status, "IEC 60364-5-52:2009 BASE-EDITION VERIFIED")
        self.assertEqual(r.base_iz_a, 298.0)
        self.assertEqual(r.iz_a, 298.0)

    def test_aluminium_185_reference_condition(self):
        r = calculate_supported_iz(self._base(material="aluminium", cross_section_mm2=185))
        self.assertEqual(r.base_iz_a, 347.0)
        self.assertEqual(r.iz_a, 347.0)

    def test_ambient_temperature_correction(self):
        r = calculate_supported_iz(self._base(ambient_temperature_c=40))
        self.assertAlmostEqual(r.iz_a, 298.0 * 0.91)

    def test_parallel_runs_are_not_multiplied_blindly(self):
        r = calculate_supported_iz(self._base(parallel_runs=3, equal_current_sharing_confirmed=True))
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertIsNone(r.iz_a)
        self.assertTrue(any("parallel-run" in x for x in r.missing_or_unsupported))

    def test_fire_rated_or_other_insulation_not_assumed_generic_xlpe(self):
        r = calculate_supported_iz(self._base(insulation="other"))
        self.assertEqual(r.status, "NOT VERIFIED")

    def test_high_harmonics_block_lookup(self):
        r = calculate_supported_iz(self._base(thdi_percent=20, neutral_loaded=True))
        self.assertEqual(r.status, "NOT VERIFIED")

    def test_unknown_temperature_is_not_interpolated_or_guessed(self):
        r = calculate_supported_iz(self._base(ambient_temperature_c=37))
        self.assertEqual(r.status, "NOT VERIFIED")


if __name__ == "__main__":
    unittest.main()
