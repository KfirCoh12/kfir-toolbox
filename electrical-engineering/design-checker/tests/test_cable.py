import unittest

from src.cable import CableAmpacityInput, calculate_supported_iz


class CableAmpacityInputTests(unittest.TestCase):
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
            grouping_arrangement=None,
            parallel_runs=1,
            equal_current_sharing_confirmed=None,
            thdi_percent=0,
            neutral_loaded=False,
        )
        values.update(overrides)
        return CableAmpacityInput(**values)

    def test_supported_reference_case_returns_verified_iz(self):
        result = calculate_supported_iz(self._base())
        self.assertEqual(result.iz_a, 298.0)
        self.assertEqual(result.missing_or_unsupported, ())
        self.assertIn("IEC 60364-5-52:2009", result.status)

    def test_missing_ambient_condition_is_not_guessed(self):
        result = calculate_supported_iz(self._base(ambient_temperature_c=None))
        self.assertIsNone(result.iz_a)
        self.assertIn("ambient_temperature_c is required", result.missing_or_unsupported)

    def test_parallel_runs_require_current_sharing_confirmation(self):
        result = calculate_supported_iz(
            self._base(
                parallel_runs=3,
                grouped_circuits=3,
                grouping_arrangement="ladder",
                equal_current_sharing_confirmed=False,
            )
        )
        self.assertIsNone(result.iz_a)
        self.assertTrue(any("current sharing" in item for item in result.missing_or_unsupported))

    def test_ground_installation_is_outside_current_v0_slice(self):
        result = calculate_supported_iz(
            self._base(
                environment="ground",
                installation_method="D",
                ambient_temperature_c=None,
                ground_temperature_c=20,
                soil_thermal_resistivity_km_per_w=2.5,
            )
        )
        self.assertIsNone(result.iz_a)
        self.assertTrue(any("air installations only" in item for item in result.missing_or_unsupported))

    def test_high_thdi_is_flagged_not_approximated(self):
        result = calculate_supported_iz(self._base(thdi_percent=20, neutral_loaded=True))
        self.assertIsNone(result.iz_a)
        self.assertTrue(any("THDi > 15%" in item for item in result.missing_or_unsupported))


if __name__ == "__main__":
    unittest.main()
