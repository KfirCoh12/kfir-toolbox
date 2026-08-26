import unittest

from src.ampacity_router import RoutedAmpacityInput, calculate_routed_ampacity
from src.current import calculate_design_current
from src.manufacturer_ampacity import get_nhxh_fe180_e90_air_30c
from src.voltage_drop import calculate_voltage_drop


class CrossModuleConsistencyTests(unittest.TestCase):
    def test_nhxh_phase_section_drives_voltage_drop_geometry(self):
        record = get_nhxh_fe180_e90_air_30c("3x95+50")
        self.assertIsNotNone(record)
        self.assertEqual(record.phase_conductor_mm2, 95.0)

        current = calculate_design_current(
            load_type="kw",
            load_value=97.0,
            voltage_v=400.0,
            phase="three",
            power_factor=0.90,
        )
        vd = calculate_voltage_drop(
            current_a=current.design_current_a,
            length_m=100.0,
            cross_section_mm2=record.phase_conductor_mm2,
            system_voltage_v=400.0,
            phase="three",
            material="copper",
            power_factor=0.90,
            permitted_limit_percent=5.0,
            limit_source="regression criterion",
            allow_annex_g_defaults=True,
        )
        self.assertGreater(vd.voltage_drop_percent, 0.5)
        self.assertLess(vd.voltage_drop_percent, 5.0)

    def test_manufacturer_ampacity_preserves_source_identity(self):
        result = calculate_routed_ampacity(
            RoutedAmpacityInput(
                source_kind="manufacturer_nhxh_fe180_e90",
                construction="3x95+50",
                ambient_temperature_c=30.0,
                grouped_circuits=1,
                parallel_runs=1,
            )
        )
        self.assertEqual(result.iz_a, 305.0)
        self.assertEqual(result.source_metadata["source_kind"], "manufacturer")
        self.assertEqual(result.source_metadata["construction"], "3x95+50")
        self.assertNotIn("iec_generic", str(result.source_metadata).lower())

    def test_unsourced_manufacturer_correction_cannot_produce_iz(self):
        result = calculate_routed_ampacity(
            RoutedAmpacityInput(
                source_kind="manufacturer_nhxh_fe180_e90",
                construction="3x95+50",
                ambient_temperature_c=30.0,
                grouped_circuits=2,
                parallel_runs=1,
            )
        )
        self.assertIsNone(result.iz_a)
        self.assertIn("NOT VERIFIED", result.status)
        self.assertTrue(any("grouping correction" in item for item in result.missing_or_unsupported))


if __name__ == "__main__":
    unittest.main()
