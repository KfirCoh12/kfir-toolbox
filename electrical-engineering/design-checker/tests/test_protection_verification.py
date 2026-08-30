import unittest

from src.protection_verification import (
    EvidenceSource,
    ProtectionVerificationResult,
    VerificationProvenance,
    VerifierIdentity,
    assert_result_matches_pair,
    make_unverified_result,
    make_verified_result,
)


class ProtectionVerificationContractTests(unittest.TestCase):
    def _provenance(self):
        return VerificationProvenance(
            upstream_node_id="UP:device",
            downstream_node_id="DOWN:device",
            verifier=VerifierIdentity(name="future-breaking-capacity-verifier", version="0.1"),
            evidence_sources=(
                EvidenceSource(
                    kind="ENGINEERING_RECORD",
                    reference="DECLARED-EVIDENCE-01",
                ),
            ),
            rule_basis_ref="TRACEABLE-RULE-BASIS-01",
        )

    def test_unrequested_result_is_not_checked_and_has_no_provenance(self):
        result = make_unverified_result(
            check="SELECTIVITY",
            requested=False,
            missing_evidence=("manufacturer table",),
            basis="No selectivity check requested.",
        )
        self.assertEqual(result.status, "NOT CHECKED")
        self.assertIsNone(result.provenance)
        self.assertEqual(result.missing_evidence, ())

    def test_requested_unverified_result_is_insufficient_data(self):
        result = make_unverified_result(
            check="SELECTIVITY",
            requested=True,
            missing_evidence=("manufacturer table",),
            basis="A dedicated selectivity verifier has not established a verdict.",
        )
        self.assertEqual(result.status, "INSUFFICIENT DATA")
        self.assertIsNone(result.provenance)
        self.assertEqual(result.missing_evidence, ("manufacturer table",))

    def test_verified_result_requires_traceable_provenance(self):
        result = make_verified_result(
            check="BREAKING_CAPACITY",
            provenance=self._provenance(),
            basis="Dedicated verifier established the result from its declared rule and evidence.",
        )
        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.provenance.pair_key, ("UP:device", "DOWN:device"))
        self.assertEqual(result.missing_evidence, ())

    def test_verified_result_rejects_missing_evidence_source(self):
        provenance = VerificationProvenance(
            upstream_node_id="UP:device",
            downstream_node_id="DOWN:device",
            verifier=VerifierIdentity(name="verifier", version="1"),
            evidence_sources=(),
            rule_basis_ref="RULE-01",
        )
        with self.assertRaisesRegex(ValueError, "at least one traceable evidence source"):
            make_verified_result(
                check="FAULT_PROTECTION",
                provenance=provenance,
                basis="engineering basis",
            )

    def test_verified_result_rejects_missing_verifier_identity(self):
        provenance = VerificationProvenance(
            upstream_node_id="UP:device",
            downstream_node_id="DOWN:device",
            verifier=VerifierIdentity(name="", version="1"),
            evidence_sources=(EvidenceSource(kind="CALCULATION", reference="CALC-01"),),
            rule_basis_ref="RULE-01",
        )
        with self.assertRaisesRegex(ValueError, "verifier name and version"):
            make_verified_result(
                check="CABLE_PROTECTION",
                provenance=provenance,
                basis="engineering basis",
            )

    def test_verified_result_rejects_blank_rule_basis(self):
        provenance = VerificationProvenance(
            upstream_node_id="UP:device",
            downstream_node_id="DOWN:device",
            verifier=VerifierIdentity(name="verifier", version="1"),
            evidence_sources=(EvidenceSource(kind="CALCULATION", reference="CALC-01"),),
            rule_basis_ref="  ",
        )
        with self.assertRaisesRegex(ValueError, "rule basis"):
            make_verified_result(
                check="BREAKING_CAPACITY",
                provenance=provenance,
                basis="engineering basis",
            )

    def test_pair_guard_rejects_reusing_verified_result_on_another_pair(self):
        result = make_verified_result(
            check="BREAKING_CAPACITY",
            provenance=self._provenance(),
            basis="engineering basis",
        )
        with self.assertRaisesRegex(ValueError, "different protection relationship"):
            assert_result_matches_pair(
                result,
                upstream_node_id="OTHER:device",
                downstream_node_id="DOWN:device",
            )

    def test_pair_guard_allows_unverified_result_without_provenance(self):
        result = make_unverified_result(
            check="SELECTIVITY",
            requested=True,
            basis="not verified",
        )
        assert_result_matches_pair(
            result,
            upstream_node_id="ANY:device",
            downstream_node_id="OTHER:device",
        )

    def test_plain_dataclass_verified_without_provenance_is_detected_by_pair_guard(self):
        malformed = ProtectionVerificationResult(
            check="SELECTIVITY",
            status="VERIFIED",
            provenance=None,
            basis="malformed external construction",
        )
        with self.assertRaisesRegex(ValueError, "invalid without provenance"):
            assert_result_matches_pair(
                malformed,
                upstream_node_id="UP:device",
                downstream_node_id="DOWN:device",
            )


if __name__ == "__main__":
    unittest.main()
