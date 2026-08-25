import math
import unittest

from src.voltage_drop import (
    annex_g_guidance_limit_percent,
    calculate_voltage_drop,
)


class VoltageDropTests(unittest.TestCase):
    def test_three_phase_annex_g_calculation(self):
        r = calculate_voltage_drop(
            current_a=100,
            length_m=100,
            cross_section_mm2=95,
            system_voltage_v=400,
            phase="three",
            material="copper",
            power_factor=0.9,
            allow_annex_g_defaults=True,
        )
        rho = 0.0225
        x = 0.00008
        sin_phi = math.sqrt(1 - 0.9**2)
        expected_v = ((rho * 100 / 95 * 0.9) + (x * 100 * sin_phi)) * 100
        expected_pct = 100 * expected_v / (400 / math.sqrt(3))
        self.assertAlmostEqual(r.voltage_drop_v, expected_v, places=8)
        self.assertAlmostEqual(r.voltage_drop_percent, expected_pct, places=8)

    def test_single_phase_uses_b_equals_two(self):
        r = calculate_voltage_drop(
            current_a=20,
            length_m=50,
            cross_section_mm2=10,
            system_voltage_v=230,
            phase="single",
            material="copper",
            power_factor=1.0,
            allow_annex_g_defaults=True,
        )
        expected_v = 2 * (0.0225 * 50 / 10) * 20
        self.assertAlmostEqual(r.voltage_drop_v, expected_v, places=8)

    def test_defaults_are_never_silent(self):
        with self.assertRaises(ValueError):
            calculate_voltage_drop(
                current_a=100,
                length_m=100,
                cross_section_mm2=95,
                system_voltage_v=400,
                phase="three",
                material="copper",
                power_factor=None,
            )

    def test_explicit_limit_requires_source(self):
        with self.assertRaises(ValueError):
            calculate_voltage_drop(
                current_a=100,
                length_m=100,
                cross_section_mm2=95,
                system_voltage_v=400,
                phase="three",
                material="copper",
                power_factor=0.9,
                allow_annex_g_defaults=True,
                permitted_limit_percent=5,
            )

    def test_limit_comparison_is_separate(self):
        r = calculate_voltage_drop(
            current_a=50,
            length_m=20,
            cross_section_mm2=25,
            system_voltage_v=400,
            phase="three",
            material="copper",
            power_factor=0.9,
            allow_annex_g_defaults=True,
            permitted_limit_percent=5,
            limit_source="project criterion",
        )
        self.assertEqual(r.comparison, "PASS")
        self.assertEqual(r.limit_source, "project criterion")

    def test_annex_g_public_lv_guidance(self):
        self.assertEqual(
            annex_g_guidance_limit_percent(supply_type="public_lv", use_type="lighting"),
            3.0,
        )
        self.assertEqual(
            annex_g_guidance_limit_percent(supply_type="public_lv", use_type="other"),
            5.0,
        )

    def test_long_main_wiring_guidance_is_capped(self):
        self.assertAlmostEqual(
            annex_g_guidance_limit_percent(
                supply_type="public_lv", use_type="other", main_wiring_length_m=150
            ),
            5.25,
        )
        self.assertAlmostEqual(
            annex_g_guidance_limit_percent(
                supply_type="public_lv", use_type="other", main_wiring_length_m=500
            ),
            5.5,
        )


if __name__ == "__main__":
    unittest.main()
