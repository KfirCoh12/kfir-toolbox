import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.protection_evidence import CoordinationEvidence, FaultEvidence, ProtectiveDeviceEvidence
from src.protection_verification_hierarchy import hierarchy_breaking_capacity_verifications


class ProtectionVerificationHierarchyTests(unittest.TestCase):
    def _evidence(self, *, fault_ka: float, capacity_ka: float):
        return CoordinationEvidence(
            downstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="DEVICE",
                rating_a=32.0,
                breaking_capacity_ka=capacity_ka,
            ),
            fault=FaultEvidence(prospective_fault_current_ka=fault_ka),
        )

    def test_no_requested_pairs_produces_not_checked_for_every_relationship(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        results = hierarchy_breaking_capacity_verifications(graph)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].result.status, "NOT CHECKED")

    def test_requested_pair_can_verify_without_promoting_sibling_pair(self):
        graph = make_radial_board_graph(board_id="DB", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Load 1")
        graph = add_radial_circuit(graph, circuit_id="C-02", description="Load 2")
        pair_1 = ("incomer", "C-01:device")
        pair_2 = ("incomer", "C-02:device")

        results = hierarchy_breaking_capacity_verifications(
            graph,
            evidence_by_pair={pair_1: self._evidence(fault_ka=6.0, capacity_ka=10.0)},
            requested_pairs={pair_1},
            rule_basis_ref_by_pair={pair_1: "PROJECT-BC-RULE-01"},
            evidence_record_ref_by_pair={pair_1: "FAULT-STUDY-01"},
        )
        by_pair = {item.pair_key: item.result for item in results}
        self.assertEqual(by_pair[pair_1].status, "VERIFIED")
        self.assertEqual(by_pair[pair_2].status, "NOT CHECKED")

    def test_failing_pair_is_not_verified_and_other_pair_remains_independent(self):
        graph = make_radial_board_graph(board_id="DB", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Load 1")
        graph = add_radial_circuit(graph, circuit_id="C-02", description="Load 2")
        pair_1 = ("incomer", "C-01:device")
        pair_2 = ("incomer", "C-02:device")

        results = hierarchy_breaking_capacity_verifications(
            graph,
            evidence_by_pair={
                pair_1: self._evidence(fault_ka=12.0, capacity_ka=10.0),
                pair_2: self._evidence(fault_ka=4.0, capacity_ka=6.0),
            },
            requested_pairs={pair_1, pair_2},
            rule_basis_ref_by_pair={pair_1: "RULE-1", pair_2: "RULE-2"},
            evidence_record_ref_by_pair={pair_1: "REC-1", pair_2: "REC-2"},
        )
        by_pair = {item.pair_key: item.result for item in results}
        self.assertEqual(by_pair[pair_1].status, "NOT VERIFIED")
        self.assertEqual(by_pair[pair_2].status, "VERIFIED")
        self.assertEqual(by_pair[pair_1].provenance.rule_basis_ref, "RULE-1")
        self.assertEqual(by_pair[pair_2].provenance.rule_basis_ref, "RULE-2")

    def test_requested_pair_missing_its_own_reference_is_insufficient_data(self):
        graph = make_radial_board_graph(board_id="DB", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Load 1")
        graph = add_radial_circuit(graph, circuit_id="C-02", description="Load 2")
        pair_1 = ("incomer", "C-01:device")
        pair_2 = ("incomer", "C-02:device")

        results = hierarchy_breaking_capacity_verifications(
            graph,
            evidence_by_pair={pair_1: self._evidence(fault_ka=5.0, capacity_ka=10.0)},
            requested_pairs={pair_1},
            rule_basis_ref_by_pair={pair_2: "SIBLING-RULE"},
            evidence_record_ref_by_pair={pair_2: "SIBLING-RECORD"},
        )
        by_pair = {item.pair_key: item.result for item in results}
        self.assertEqual(by_pair[pair_1].status, "INSUFFICIENT DATA")
        self.assertIn("traceable breaking-capacity rule basis reference", by_pair[pair_1].missing_evidence)
        self.assertIn(
            "traceable evidence record reference for declared numeric inputs",
            by_pair[pair_1].missing_evidence,
        )

    def test_nested_hierarchy_verifies_exact_adjacent_pair(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Sub board",
        )
        pair = ("F-01:device", "F-01:DB-L1:incomer")
        results = hierarchy_breaking_capacity_verifications(
            graph,
            evidence_by_pair={pair: self._evidence(fault_ka=8.0, capacity_ka=16.0)},
            requested_pairs={pair},
            rule_basis_ref_by_pair={pair: "PROJECT-BC-RULE-01"},
            evidence_record_ref_by_pair={pair: "FAULT-STUDY-DB-L1"},
        )
        by_pair = {item.pair_key: item.result for item in results}
        self.assertEqual(by_pair[pair].status, "VERIFIED")
        self.assertEqual(by_pair[pair].provenance.pair_key, pair)

    def test_unknown_pair_inputs_fail_conservatively(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        unknown = ("missing-up", "missing-down")
        with self.assertRaisesRegex(ValueError, "unknown protection relationship"):
            hierarchy_breaking_capacity_verifications(
                graph,
                requested_pairs={unknown},
            )


if __name__ == "__main__":
    unittest.main()
