import unittest

from src.circuit_engine import CircuitDesignRequest, calculate_circuit_design


class CircuitEngineTests(unittest.TestCase):
    def test_named_circuit_wraps_existing_selector(self):
        r = calculate_circuit_design(CircuitDesignRequest(
            circuit_id="C-01",
            description="AHU-01",
            load_type="kw",
            load_value=30,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            demand_factor=0.8,
            material="copper",
        ))
        self.assertEqual(r.request.circuit_id, "C-01")
        self.assertEqual(r.request.description, "AHU-01")
        self.assertAlmostEqual(r.design_current_a, r.selection.current.design_current_a)
        self.assertEqual(r.breaker_a, 40.0)
        self.assertEqual(r.cable_mm2, 10.0)
        self.assertEqual(r.cable_runs, 1)
        self.assertEqual(r.connection_rating_a, 63.0)
        self.assertEqual(r.verification.scope_status, "SUPPORTED_SCOPE")

    def test_material_is_explicit_and_preserved(self):
        r = calculate_circuit_design(CircuitDesignRequest(
            circuit_id="C-02",
            description="Process load",
            load_type="kw",
            load_value=30,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            material="aluminium",
        ))
        self.assertEqual(r.request.material, "aluminium")
        self.assertIsNotNone(r.cable_mm2)

    def test_voltage_drop_is_exposed_as_board_friendly_field(self):
        r = calculate_circuit_design(CircuitDesignRequest(
            circuit_id="C-03",
            description="Remote load",
            load_type="kw",
            load_value=20,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
            length_m=50,
            permitted_voltage_drop_percent=5.0,
            voltage_drop_limit_source="Project criterion",
            allow_annex_g_defaults=True,
        ))
        self.assertIsNotNone(r.voltage_drop_percent)
        self.assertEqual(r.selection.voltage_drop.comparison, "PASS")

    def test_single_phase_uses_two_loaded_conductor_ampacity_path(self):
        r = calculate_circuit_design(CircuitDesignRequest(
            circuit_id="C-04",
            description="Single-phase appliance",
            load_type="kw",
            load_value=5,
            voltage_v=230,
            phase="single",
            power_factor=0.9,
        ))
        self.assertEqual(r.verification.scope_status, "SUPPORTED_SCOPE")
        self.assertEqual(r.breaker_a, 25.0)
        self.assertEqual(r.cable_mm2, 1.5)
        self.assertEqual(r.cable_runs, 1)
        self.assertFalse(r.verification.blocking_issues)
        self.assertTrue(
            any("harmonic-rich neutral loading" in item for item in r.selection.limitations)
        )

    def test_circuit_identity_is_required(self):
        with self.assertRaises(ValueError):
            calculate_circuit_design(CircuitDesignRequest(
                circuit_id=" ",
                description="Load",
                load_type="kw",
                load_value=5,
                voltage_v=400,
                phase="three",
                power_factor=0.9,
            ))
        with self.assertRaises(ValueError):
            calculate_circuit_design(CircuitDesignRequest(
                circuit_id="C-05",
                description=" ",
                load_type="kw",
                load_value=5,
                voltage_v=400,
                phase="three",
                power_factor=0.9,
            ))


if __name__ == "__main__":
    unittest.main()
