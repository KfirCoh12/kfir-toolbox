import unittest
from src.cable import CableAmpacityInput, validate_ampacity_inputs


class CableAmpacityInputTests(unittest.TestCase):
    def test_missing_conditions_are_not_guessed(self):
        data = CableAmpacityInput(
            material="copper",
            cross_section_mm2=95,
            insulation="xlpe_epr",
            loaded_conductors=3,
            installation_method=None,
            environment="air",
        )
        r = validate_ampacity_inputs(data)
        self.assertFalse(r.ready_for_iz_lookup)
        self.assertIn("installation_method", r.missing_or_unverified)
        self.assertIn("ambient_temperature_c", r.missing_or_unverified)
        self.assertIn("cable_data_source", r.missing_or_unverified)
        self.assertEqual(r.standards_status, "NOT VERIFIED")

    def test_complete_single_run_air_case_is_ready_for_lookup(self):
        data = CableAmpacityInput(
            material="copper",
            cross_section_mm2=95,
            insulation="xlpe_epr",
            loaded_conductors=3,
            installation_method="C",
            environment="air",
            ambient_temperature_c=30,
            grouped_circuits=1,
            parallel_runs=1,
            thdi_percent=5,
            neutral_loaded=False,
            cable_data_source="IEC 60364-5-52:2009 Ed.3.0",
            source_table_or_method="Annex B applicable table",
        )
        r = validate_ampacity_inputs(data)
        self.assertTrue(r.ready_for_iz_lookup)
        self.assertEqual(r.missing_or_unverified, ())
        self.assertEqual(r.standards_status, "CALCULATED INPUTS READY — IZ NOT YET IMPLEMENTED")

    def test_parallel_runs_require_current_sharing_confirmation(self):
        data = CableAmpacityInput(
            material="aluminium",
            cross_section_mm2=240,
            insulation="xlpe_epr",
            loaded_conductors=3,
            installation_method="F",
            environment="air",
            ambient_temperature_c=30,
            grouped_circuits=3,
            parallel_runs=3,
            equal_current_sharing_confirmed=False,
            thdi_percent=5,
            neutral_loaded=False,
            cable_data_source="IEC 60364-5-52:2009 Ed.3.0",
            source_table_or_method="Annex B applicable table",
        )
        r = validate_ampacity_inputs(data)
        self.assertFalse(r.ready_for_iz_lookup)
        self.assertIn("equal_current_sharing_confirmed", r.missing_or_unverified)

    def test_ground_case_requires_ground_conditions(self):
        data = CableAmpacityInput(
            material="aluminium",
            cross_section_mm2=185,
            insulation="xlpe_epr",
            loaded_conductors=3,
            installation_method="D",
            environment="ground",
            grouped_circuits=1,
            thdi_percent=0,
            neutral_loaded=False,
            cable_data_source="IEC 60364-5-52:2009 Ed.3.0",
            source_table_or_method="Annex B applicable table",
        )
        r = validate_ampacity_inputs(data)
        self.assertIn("ground_temperature_c", r.missing_or_unverified)
        self.assertIn("soil_thermal_resistivity_km_per_w", r.missing_or_unverified)

    def test_high_thdi_is_flagged(self):
        data = CableAmpacityInput(
            material="copper",
            cross_section_mm2=50,
            insulation="pvc",
            loaded_conductors=3,
            installation_method="C",
            environment="air",
            ambient_temperature_c=30,
            grouped_circuits=1,
            thdi_percent=20,
            neutral_loaded=True,
            cable_data_source="IEC 60364-5-52:2009 Ed.3.0",
            source_table_or_method="Annex B + Annex E",
        )
        r = validate_ampacity_inputs(data)
        self.assertTrue(any("THDi exceeds 15%" in note for note in r.notes))


if __name__ == "__main__":
    unittest.main()
