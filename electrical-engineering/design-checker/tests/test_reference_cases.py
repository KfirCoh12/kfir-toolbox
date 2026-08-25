import unittest

from src.current import calculate_design_current


REFERENCE_CASES = (
    # name, load_kW, source current A, source adjusted current A, inferred source margin
    ("case_01", 97, 155.2, 194.0, 0.8),
    ("case_02", 282, 451.2, 564.0, 0.8),
    ("case_03", 390, 624.0, 780.0, 0.8),
    ("case_04", 748, 1196.8, 1329.7777777777776, 0.9),
    ("case_05", 22, 35.2, 39.111111111111114, 0.9),
    ("case_06", 11, 17.6, 22.0, 0.8),
)


class ReferenceCaseRegressionTests(unittest.TestCase):
    def test_missing_pf_blocks_all_kw_reference_cases(self):
        for name, load_kw, *_ in REFERENCE_CASES:
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    calculate_design_current(
                        load_type="kw",
                        load_value=load_kw,
                        voltage_v=400,
                        phase="three",
                    )

    def test_400v_three_phase_pf_09_tracks_source_current_shortcut(self):
        """Comparison only: this does not prove the source assumption or IEC compliance."""
        for name, load_kw, source_current, *_ in REFERENCE_CASES:
            with self.subTest(case=name):
                result = calculate_design_current(
                    load_type="kw",
                    load_value=load_kw,
                    voltage_v=400,
                    phase="three",
                    power_factor=0.9,
                )
                relative_difference = abs(result.design_current_a - source_current) / source_current
                self.assertLess(relative_difference, 0.003)
                self.assertEqual(result.standards_status, "CALCULATED — NOT IEC VERIFIED")

    def test_source_adjusted_current_is_not_one_uniform_margin(self):
        inferred = {}
        for name, _, source_current, source_adjusted, expected_margin in REFERENCE_CASES:
            margin = source_current / source_adjusted
            inferred[name] = margin
            self.assertAlmostEqual(margin, expected_margin, places=9)

        self.assertAlmostEqual(inferred["case_01"], 0.8)
        self.assertAlmostEqual(inferred["case_04"], 0.9)

    def test_explicit_margin_reproduces_source_adjustment_pattern(self):
        """Project-margin reproduction remains separate from Ib and IEC rules."""
        for name, load_kw, _, _, margin in REFERENCE_CASES:
            with self.subTest(case=name):
                result = calculate_design_current(
                    load_type="kw",
                    load_value=load_kw,
                    voltage_v=400,
                    phase="three",
                    power_factor=0.9,
                    design_margin=margin,
                )
                self.assertIsNotNone(result.margin_adjusted_current_a)
                self.assertEqual(result.design_margin, margin)
                self.assertEqual(result.standards_status, "CALCULATED — NOT IEC VERIFIED")


if __name__ == "__main__":
    unittest.main()
