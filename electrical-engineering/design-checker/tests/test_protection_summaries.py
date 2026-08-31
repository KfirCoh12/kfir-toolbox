import unittest

from src.board_graph import add_radial_circuit, make_radial_board_graph
from src.protection_evidence import CoordinationEvidence, FaultEvidence, ProtectiveDeviceEvidence
from src.protection_summaries import protection_pair_summaries


class ProtectionSummaryTests(unittest.TestCase):
    def _evidence(self, *, fault_ka: float, capacity_ka: float):
        return CoordinationEvidence(
            upstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="UP",
                rating_a=63.0,
            ),
            downstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="DOWN",
                rating_a=16.0,
                breaking_capacity_ka=capacity_ka,
            ),
            fault=FaultEvidence(prospective_fault_current_ka=fault_ka),
        )

    def test_summary_keeps_breaking_capacity_separate_from_overall_protection(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        pair = ("incomer", "C-01:device")
        summary = protection_pair_summaries(
            graph,
            evidence_by_pair={pair: self._evidence(fault_ka=6.0, capacity_ka=10.0)},
            protection_check_requested=True,
            breaking_capacity_requested_pairs={pair},
            breaking_capacity_rule_basis_ref_by_pair={pair: "PROJECT-BC-RULE-01"},
            breaking_capacity_evidence_record_ref_by_pair={pair: "FAULT-STUDY-01"},
        )[0]

        self.assertEqual(summary.breaking_capacity_status, "VERIFIED")
        self.assertEqual(summary.protection_status, "INSUFFICIENT DATA")
        self.assertNotEqual(summary.protection_status, "VERIFIED")
        self.assertEqual(summary.selectivity_status, "NOT CHECKED")
        self.assertEqual(summary.breaking_capacity_rule_basis_ref, "PROJECT-BC-RULE-01")
        self.assertIsNotNone(summary.breaking_capacity_verifier)

    def test_negative_breaking_capacity_verdict_is_exposed_without_overwriting_other_statuses(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        pair = ("incomer", "C-01:device")
        summary = protection_pair_summaries(
            graph,
            evidence_by_pair={pair: self._evidence(fault_ka=12.0, capacity_ka=10.0)},
            selectivity_check_requested=True,
            breaking_capacity_requested_pairs={pair},
            breaking_capacity_rule_basis_ref_by_pair={pair: "PROJECT-BC-RULE-01"},
            breaking_capacity_evidence_record_ref_by_pair={pair: "FAULT-STUDY-01"},
        )[0]

        self.assertEqual(summary.breaking_capacity_status, "NOT VERIFIED")
        self.assertEqual(summary.protection_status, "NOT CHECKED")
        self.assertEqual(summary.selectivity_status, "INSUFFICIENT DATA")

    def test_unrequested_breaking_capacity_has_no_verifier_provenance(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        summary = protection_pair_summaries(graph)[0]

        self.assertEqual(summary.breaking_capacity_status, "NOT CHECKED")
        self.assertIsNone(summary.breaking_capacity_rule_basis_ref)
        self.assertIsNone(summary.breaking_capacity_verifier)
        self.assertIsNone(summary.breaking_capacity_verifier_version)

    def test_pair_summaries_preserve_independent_sibling_results(self):
        graph = make_radial_board_graph(board_id="DB", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Load 1")
        graph = add_radial_circuit(graph, circuit_id="C-02", description="Load 2")
        pair_1 = ("incomer", "C-01:device")
        pair_2 = ("incomer", "C-02:device")

        summaries = protection_pair_summaries(
            graph,
            evidence_by_pair={
                pair_1: self._evidence(fault_ka=4.0, capacity_ka=6.0),
                pair_2: self._evidence(fault_ka=8.0, capacity_ka=6.0),
            },
            breaking_capacity_requested_pairs={pair_1, pair_2},
            breaking_capacity_rule_basis_ref_by_pair={pair_1: "RULE-1", pair_2: "RULE-2"},
            breaking_capacity_evidence_record_ref_by_pair={pair_1: "REC-1", pair_2: "REC-2"},
        )
        by_pair = {summary.pair_key: summary for summary in summaries}
        self.assertEqual(by_pair[pair_1].breaking_capacity_status, "VERIFIED")
        self.assertEqual(by_pair[pair_2].breaking_capacity_status, "NOT VERIFIED")
        self.assertEqual(by_pair[pair_1].breaking_capacity_rule_basis_ref, "RULE-1")
        self.assertEqual(by_pair[pair_2].breaking_capacity_rule_basis_ref, "RULE-2")


if __name__ == "__main__":
    unittest.main()
