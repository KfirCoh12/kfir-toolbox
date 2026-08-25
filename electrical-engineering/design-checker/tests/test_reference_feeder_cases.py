"""End-to-end status regression for the six anonymized private-workbook cases.

Only sanitized technical values are represented here. The source workbook is
not authoritative, and missing installation/product data are deliberately not
guessed.
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
    def test_all_cases_preserve_private_source_as_reference_not_authority(self):
        for name, kw, breaker, material, size, runs, length, generic_ok in CASES:
            with self.subTest(case=name):
                # 400 V / 3ph / PF 0.9 is the explicit comparison assumption used
                # by the earlier regression work; it is not claimed to be stated
                # in the private workbook.
                if generic_ok:
                    cable = CableAmpacityInput(
                        material=material,
                        cross_section_mm2=size,
                        insulation="xlpe_epr",
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
                else:
                    # Fire-performance cable cases remain intentionally outside
                    # the generic XLPE dataset until a defensible product/current
                    # rating source is added.
                    cable = CableAmpacityInput(
                        material=material,
                        cross_section_mm2=size,
                        insulation="other",
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

                r = check_feeder(FeederInput(
                    load_type="kw", load_value=kw, voltage_v=400, phase="three",
                    power_factor=0.9, breaker_in_a=breaker, cable=cable,
                    length_m=length,
                    voltage_drop_cross_section_mm2=size,
                    voltage_drop_material=material,
                    allow_annex_g_defaults=True,
                ))

                # Until current 4-43 is verified, none of the six cases may
                # become an overall PASS merely because the arithmetic works.
                self.assertNotEqual(r.overall_outcome, "PASS")
                if not generic_ok:
                    self.assertEqual(r.ampacity_comparison.comparison, "NOT VERIFIED")
                self.assertTrue(r.missing_or_unverified)


if __name__ == "__main__": unittest.main()
