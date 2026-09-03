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

    def test_copper_95_reference_condition(self):
        r = calculate_supported_iz(self._base())
        self.assertEqual(r.status, "IEC 60364-5-52:2009 BASE-EDITION VERIFIED")
        self.assertEqual(r.base_iz_a, 298.0)
        self.assertEqual(r.iz_a, 298.0)

    def test_two_loaded_copper_method_e_reference_condition(self):
        r = calculate_supported_iz(self._base(
            cross_section_mm2=1.5,
            loaded_conductors=2,
            neutral_loaded=True,
        ))
        self.assertEqual(r.status, "IEC 60364-5-52:2009 BASE-EDITION VERIFIED")
        self.assertEqual(r.base_iz_a, 26.0)
        self.assertEqual(r.iz_a, 26.0)
        self.assertTrue(any("two loaded conductors" in line for line in r.trace))

    def test_two_loaded_aluminium_method_e_reference_condition(self):
        r = calculate_supported_iz(self._base(
            material="aluminium",
            cross_section_mm2=2.5,
            loaded_conductors=2,
            neutral_loaded=True,
        ))
        self.assertEqual(r.base_iz_a, 28.0)
        self.assertEqual(r.iz_a, 28.0)

    def test_loaded_conductor_count_outside_verified_slice_is_not_guessed(self):
        r = calculate_supported_iz(self._base(loaded_conductors=4))
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertIsNone(r.iz_a)
        self.assertTrue(any("two or three loaded conductors" in x for x in r.missing_or_unsupported))

    def test_ambient_temperature_correction(self):
        r = calculate_supported_iz(self._base(ambient_temperature_c=40))
        self.assertAlmostEqual(r.iz_a, 298.0 * 0.91)

    def test_grouping_on_ladder(self):
        r = calculate_supported_iz(self._base(grouped_circuits=3, grouping_arrangement="ladder_single_layer"))
        self.assertAlmostEqual(r.iz_a, 298.0 * 0.82)
        self.assertIn(("grouping", 0.82), r.correction_factors)

    def test_grouping_requires_known_arrangement(self):
        r = calculate_supported_iz(self._base(grouped_circuits=3))
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertIsNone(r.iz_a)

    def test_three_parallel_runs_are_guarded_and_grouped(self):
        r = calculate_supported_iz(self._base(
            material="aluminium",
            cross_section_mm2=185,
            grouped_circuits=3,
            grouping_arrangement="ladder_single_layer",
            parallel_runs=3,
            equal_current_sharing_confirmed=True,
        ))
        self.assertAlmostEqual(r.iz_a, 347.0 * 0.82 * 3)
        self.assertTrue(any("Aggregate Iz" in line for line in r.trace))

    def test_parallel_runs_without_current_sharing_confirmation_fail_safe(self):
        r = calculate_supported_iz(self._base(
            grouped_circuits=3,
            grouping_arrangement="ladder_single_layer",
            parallel_runs=3,
        ))
        self.assertEqual(r.status, "NOT VERIFIED")
        self.assertIsNone(r.iz_a)

    def test_parallel_runs_must_be_included_in_grouping_count(self):
        r = calculate_supported_iz(self._base(
            grouped_circuits=2,
            grouping_arrangement="ladder_single_layer",
            parallel_runs=3,
            equal_current_sharing_confirmed=True,
        ))
        self.assertEqual(r.status, "NOT VERIFIED")

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
