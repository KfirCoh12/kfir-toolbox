import unittest

from src.breaking_capacity_verifier import verify_breaking_capacity
from src.protection_evidence import CoordinationEvidence, FaultEvidence, ProtectiveDeviceEvidence
from src.protection_verification import assert_result_matches_pair


class BreakingCapacityVerifierTests(unittest.TestCase):
    def _evidence(self, *, fault_ka=8.0, capacity_ka=10.0):
        return CoordinationEvidence(
            downstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="DEVICE-01",
                rating_a=32.0,
                breaking_capacity_ka=capacity_ka,
            ),
            fault=FaultEvidence(prospective_fault_current_ka=fault_ka),
        )

    def test_unrequested_check_is_not_checked(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(),
            requested=False,
        )
        self.assertEqual(result.status, "NOT CHECKED")
        self.assertIsNone(result.provenance)

    def test_missing_numeric_inputs_are_insufficient_data(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=CoordinationEvidence(),
            rule_basis_ref="PROJECT-RULE-01",
            evidence_record_ref="FAULT-STUDY-01",
        )
        self.assertEqual(result.status, "INSUFFICIENT DATA")
        self.assertIn(
            "positive prospective fault current at the protected point",
            result.missing_evidence,
        )
        self.assertIn(
            "positive downstream device breaking capacity",
            result.missing_evidence,
        )

    def test_missing_traceability_is_insufficient_even_with_numeric_inputs(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(),
        )
        self.assertEqual(result.status, "INSUFFICIENT DATA")
        self.assertIn("traceable breaking-capacity rule basis reference", result.missing_evidence)
        self.assertIn(
            "traceable evidence record reference for declared numeric inputs",
            result.missing_evidence,
        )

    def test_capacity_above_fault_current_verifies_only_numeric_comparison(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(fault_ka=8.0, capacity_ka=10.0),
            rule_basis_ref="PROJECT-RULE-BC-01",
            evidence_record_ref="DECLARED-INPUTS-01",
        )
        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.check, "BREAKING_CAPACITY")
        self.assertEqual(result.provenance.pair_key, ("UP", "DOWN"))
        self.assertIn("10 kA", result.basis)
        self.assertIn("8 kA", result.basis)
        self.assertIn("covers only that declared numeric comparison", result.basis)

    def test_capacity_equal_to_fault_current_verifies_numeric_comparison(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(fault_ka=10.0, capacity_ka=10.0),
            rule_basis_ref="PROJECT-RULE-BC-01",
            evidence_record_ref="DECLARED-INPUTS-01",
        )
        self.assertEqual(result.status, "VERIFIED")

    def test_capacity_below_fault_current_returns_explicit_negative_verdict(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(fault_ka=12.0, capacity_ka=10.0),
            rule_basis_ref="PROJECT-RULE-BC-01",
            evidence_record_ref="DECLARED-INPUTS-01",
        )
        self.assertEqual(result.status, "NOT VERIFIED")
        self.assertIsNotNone(result.provenance)
        self.assertEqual(result.missing_evidence, ())

    def test_decisive_result_is_bound_to_exact_protection_pair(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(),
            rule_basis_ref="PROJECT-RULE-BC-01",
            evidence_record_ref="DECLARED-INPUTS-01",
        )
        with self.assertRaisesRegex(ValueError, "different protection relationship"):
            assert_result_matches_pair(
                result,
                upstream_node_id="OTHER-UP",
                downstream_node_id="DOWN",
            )

    def test_invalid_nonpositive_values_never_create_decisive_verdict(self):
        result = verify_breaking_capacity(
            upstream_node_id="UP",
            downstream_node_id="DOWN",
            evidence=self._evidence(fault_ka=-1.0, capacity_ka=0.0),
            rule_basis_ref="PROJECT-RULE-BC-01",
            evidence_record_ref="DECLARED-INPUTS-01",
        )
        self.assertEqual(result.status, "INSUFFICIENT DATA")
        self.assertIsNone(result.provenance)


if __name__ == "__main__":
    unittest.main()
