"""End-to-end status regression for six anonymized private-workbook cases.

Only sanitized technical values are represented here. The private source workbook is
not authoritative, and missing installation/product data are deliberately not guessed.
"""
import unittest

from src.cable import CableAmpacityInput
from src.feeder import FeederInput, check_feeder


CASES = (
    # name, kW, breaker A, material, mm2, runs, length m, generic-xlpe-eligible
    ("case_01", 97, 200, "copper", 95, 1, 100, False),
    ("case_02", 282, 630, "aluminium", 185, 3, 100, True),
    ("case_03", 390, 800, "aluminium", 240, 3, 200, True),
    ("case_04", 748, 1600, "copper", 120, 6, 60, False),
    ("case_05", 22, 63, "copper", 25, 1, 150, False),
    ("case_06", 11, 25, "copper", 10, 1, 100, False),
)


class SixReferenceFeederCases(unittest.TestCase):
    def _run_case(self, case):
        name, kw, breaker, material, size, runs, length, generic_ok = case
        cable = CableAmpacityInput(
            material=material,
            cross_section_mm2=size,
            insulation="xlpe_epr" if generic_ok else "other",
            loaded_conductors=3,
            installation_method="E",
            environment="air",
            ambient_temperature_c=30,
            grouped_circuits=runs,
            grouping_arrangement="bunched" if runs > 1 else None,
            parallel_runs=runs,
            equal_current_sharing_confirmed=True if runs > 1 else None,
            thdi_percent=0,
            neutral_loaded=False,
        )
        return check_feeder(FeederInput(
            load_type="kw", load_value=kw, voltage_v=400, phase="three",
            power_factor=0.9, breaker_in_a=breaker, cable=cable,
            length_m=length,
            voltage_drop_cross_section_mm2=size,
            voltage_drop_material=material,
            allow_annex_g_defaults=True,
        ))

    def test_none_of_reference_cases_can_be_overall_pass_before_4_43_verification(self):
        for case in CASES:
            with self.subTest(case=case[0]):
                r = self._run_case(case)
                self.assertNotEqual(r.overall_outcome, "PASS")
                self.assertIn("breaker protection rule/current IEC basis", r.missing_or_unverified)

    def test_fire_rated_reference_cases_stay_outside_generic_xlpe_ampacity_dataset(self):
        for case in (CASES[0], CASES[3], CASES[4], CASES[5]):
            with self.subTest(case=case[0]):
                r = self._run_case(case)
                self.assertEqual(r.ampacity_comparison.comparison, "NOT VERIFIED")
                self.assertTrue(any("XLPE/EPR only" in item for item in r.missing_or_unverified))

    def test_aluminium_cases_exercise_supported_base_dataset_under_explicit_assumptions(self):
        for case in (CASES[1], CASES[2]):
            with self.subTest(case=case[0]):
                r = self._run_case(case)
                self.assertIsNotNone(r.ampacity)
                self.assertIsNotNone(r.ampacity.iz_a)
                self.assertIn("IEC 60364-5-52:2009 BASE-EDITION VERIFIED", r.ampacity.status)
                # These are test assumptions only; they are not claimed to be stated in the private workbook.
                self.assertIn(r.ampacity_comparison.comparison, ("PASS", "FAIL"))

    def test_long_aluminium_case_voltage_drop_is_calculated_not_silently_approved(self):
        r = self._run_case(CASES[2])
        self.assertIsNotNone(r.voltage_drop)
        self.assertGreater(r.voltage_drop.voltage_drop_percent, 0)
        self.assertEqual(r.voltage_drop.comparison, "NO LIMIT CHECKED")
        self.assertIn("permitted voltage-drop limit/source", r.missing_or_unverified)


if __name__ == "__main__":
    unittest.main()
