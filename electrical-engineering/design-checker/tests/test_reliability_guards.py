import math
import unittest

from src.ampacity_router import RoutedAmpacityInput, calculate_routed_ampacity
from src.current import calculate_design_current
from src.manufacturer_ampacity import (
    get_nhxh_fe180_e90_air_30c,
    get_nhxh_phase_conductor_mm2,
)
from src.max_load import MaxLoadInput, calculate_max_load
from src.voltage_drop import calculate_voltage_drop


class ReliabilityGuardTests(unittest.TestCase):
    def test_nhxh_phase_section_is_not_concatenated_with_reduced_conductor(self):
        self.assertEqual(get_nhxh_phase_conductor_mm2("3x95+50"), 95.0)
        self.assertEqual(get_nhxh_phase_conductor_mm2("3x120+70"), 120.0)

    def test_nhxh_normalization_preserves_exact_construction_lookup(self):
        r = get_nhxh_fe180_e90_air_30c(" 3 x 95 + 50 mm² ")
        self.assertIsNotNone(r)
        self.assertEqual(r.phase_conductor_mm2, 95.0)
        self.assertEqual(r.current_capacity_air_a, 305.0)

    def test_zero_group_count_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_routed_ampacity(
                RoutedAmpacityInput(
                    source_kind="manufacturer_nhxh_fe180_e90",
                    construction="3x95+50",
                    ambient_temperature_c=30,
                    grouped_circuits=0,
                )
            )

    def test_zero_parallel_runs_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_routed_ampacity(
                RoutedAmpacityInput(
                    source_kind="manufacturer_nhxh_fe180_e90",
                    construction="3x95+50",
                    ambient_temperature_c=30,
                    parallel_runs=0,
                )
            )

    def test_voltage_drop_regression_95_not_9550_mm2(self):
        correct = calculate_voltage_drop(
            current_a=155.6,
            length_m=100,
            cross_section_mm2=95,
            system_voltage_v=400,
            phase="three",
            material="copper",
            power_factor=0.9,
            permitted_limit_percent=5,
            limit_source="regression test",
            allow_annex_g_defaults=True,
        )
        impossible = calculate_voltage_drop(
            current_a=155.6,
            length_m=100,
            cross_section_mm2=9550,
            system_voltage_v=400,
            phase="three",
            material="copper",
            power_factor=0.9,
            permitted_limit_percent=5,
            limit_source="regression test",
            allow_annex_g_defaults=True,
        )
        self.assertGreater(correct.voltage_drop_percent, 1.0)
        self.assertLess(impossible.voltage_drop_percent, 0.5)
        self.assertLess(impossible.voltage_drop_percent, correct.voltage_drop_percent / 5)

    def test_invalid_phase_never_falls_through_as_single_phase(self):
        with self.assertRaises(ValueError):
            calculate_design_current(
                load_type="kw",
                load_value=10,
                voltage_v=400,
                phase="invalid",
                power_factor=0.9,
            )
        with self.assertRaises(ValueError):
            calculate_max_load(
                MaxLoadInput(
                    voltage_v=400,
                    phase="invalid",
                    power_factor=0.9,
                    breaker_in_a=63,
                )
            )
        with self.assertRaises(ValueError):
            calculate_voltage_drop(
                current_a=20,
                length_m=50,
                cross_section_mm2=10,
                system_voltage_v=230,
                phase="invalid",
                material="copper",
                power_factor=0.9,
                allow_annex_g_defaults=True,
            )

    def test_invalid_voltage_drop_material_is_rejected_cleanly(self):
        with self.assertRaises(ValueError):
            calculate_voltage_drop(
                current_a=20,
                length_m=50,
                cross_section_mm2=10,
                system_voltage_v=230,
                phase="single",
                material="steel",
                power_factor=0.9,
                allow_annex_g_defaults=True,
            )

    def test_non_finite_engineering_inputs_are_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    calculate_design_current(
                        load_type="a",
                        load_value=bad,
                    )
                with self.assertRaises(ValueError):
                    calculate_max_load(
                        MaxLoadInput(
                            voltage_v=400,
                            phase="three",
                            power_factor=0.9,
                            breaker_in_a=bad,
                        )
                    )
                with self.assertRaises(ValueError):
                    calculate_voltage_drop(
                        current_a=bad,
                        length_m=50,
                        cross_section_mm2=10,
                        system_voltage_v=230,
                        phase="single",
                        material="copper",
                        power_factor=0.9,
                        allow_annex_g_defaults=True,
                    )


if __name__ == "__main__":
    unittest.main()
