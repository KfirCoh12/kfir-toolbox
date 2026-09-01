import math
import unittest

from src.source_fault import FaultSourceDeclaration, calculate_root_busbar_fault


class SourceFaultTests(unittest.TestCase):
    def test_carries_declared_busbar_fault_level(self):
        result = calculate_root_busbar_fault(FaultSourceDeclaration(
            kind="DECLARED_BUSBAR",
            prospective_fault_current_ka=18.5,
            evidence_record_ref="FAULT-STUDY-01",
            rule_basis_ref="PROJECT-BASIS-01",
        ))
        self.assertEqual(result.prospective_fault_current_ka, 18.5)
        self.assertEqual(result.source_kind, "DECLARED_BUSBAR")
        self.assertIn("18.5 kA", result.basis)

    def test_calculates_transformer_terminal_approximation(self):
        result = calculate_root_busbar_fault(FaultSourceDeclaration(
            kind="TRANSFORMER_TERMINAL",
            transformer_rated_power_kva=1000.0,
            transformer_secondary_voltage_v=400.0,
            transformer_impedance_percent=6.0,
            evidence_record_ref="TX-NAMEPLATE-01",
            rule_basis_ref="PROJECT-BASIS-01",
        ))
        expected = (1000.0 * 1000.0 / (math.sqrt(3.0) * 400.0)) * (100.0 / 6.0) / 1000.0
        self.assertAlmostEqual(result.prospective_fault_current_ka, expected)
        self.assertIn("Upstream source impedance is neglected", result.basis)
        self.assertIn("downstream cable impedance", result.basis)

    def test_requires_traceable_references(self):
        with self.assertRaisesRegex(ValueError, "evidence_record_ref is required"):
            calculate_root_busbar_fault(FaultSourceDeclaration(
                kind="DECLARED_BUSBAR",
                prospective_fault_current_ka=10.0,
                evidence_record_ref="",
                rule_basis_ref="PROJECT-BASIS-01",
            ))

    def test_rejects_invalid_transformer_impedance(self):
        with self.assertRaisesRegex(ValueError, "transformer_impedance_percent"):
            calculate_root_busbar_fault(FaultSourceDeclaration(
                kind="TRANSFORMER_TERMINAL",
                transformer_rated_power_kva=1000.0,
                transformer_secondary_voltage_v=400.0,
                transformer_impedance_percent=0.0,
                evidence_record_ref="TX-NAMEPLATE-01",
                rule_basis_ref="PROJECT-BASIS-01",
            ))


if __name__ == "__main__":
    unittest.main()
