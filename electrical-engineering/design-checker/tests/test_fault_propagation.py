import math
import unittest

from src.fault_propagation import (
    CableFaultPath,
    cable_conductor_resistance_ohm,
    propagate_three_phase_fault_screening,
)


class FaultPropagationTests(unittest.TestCase):
    def test_calculates_copper_conductor_resistance(self):
        path = CableFaultPath(
            circuit_id="F-01",
            material="copper",
            cross_section_mm2=25.0,
            parallel_runs=1,
            length_m=30.0,
        )
        self.assertAlmostEqual(
            cable_conductor_resistance_ohm(path),
            0.017241 * 30.0 / 25.0,
        )

    def test_parallel_runs_reduce_resistance(self):
        single = CableFaultPath("F-01", "copper", 25.0, 1, 30.0)
        parallel = CableFaultPath("F-01", "copper", 25.0, 2, 30.0)
        self.assertAlmostEqual(
            cable_conductor_resistance_ohm(parallel),
            cable_conductor_resistance_ohm(single) / 2.0,
        )

    def test_propagated_fault_is_below_upstream_fault(self):
        path = CableFaultPath("F-01", "copper", 25.0, 1, 30.0)
        result = propagate_three_phase_fault_screening(
            upstream_fault_current_ka=24.056,
            line_to_line_voltage_v=400.0,
            path=path,
        )
        self.assertLess(result.prospective_fault_current_ka, 24.056)
        expected_source_z = 400.0 / (math.sqrt(3.0) * 24.056 * 1000.0)
        self.assertAlmostEqual(result.source_impedance_magnitude_ohm, expected_source_z)
        self.assertIn("not IEC 60909", result.basis)

    def test_longer_cable_reduces_screening_current(self):
        short = propagate_three_phase_fault_screening(
            upstream_fault_current_ka=24.056,
            line_to_line_voltage_v=400.0,
            path=CableFaultPath("F-01", "copper", 25.0, 1, 10.0),
        )
        long = propagate_three_phase_fault_screening(
            upstream_fault_current_ka=24.056,
            line_to_line_voltage_v=400.0,
            path=CableFaultPath("F-01", "copper", 25.0, 1, 50.0),
        )
        self.assertLess(long.prospective_fault_current_ka, short.prospective_fault_current_ka)

    def test_rejects_invalid_length(self):
        with self.assertRaisesRegex(ValueError, "length_m"):
            cable_conductor_resistance_ohm(
                CableFaultPath("F-01", "copper", 25.0, 1, 0.0)
            )


if __name__ == "__main__":
    unittest.main()
