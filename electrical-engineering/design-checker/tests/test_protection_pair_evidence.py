import unittest
from dataclasses import replace

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.protection_evidence import (
    CableProtectionEvidence,
    CoordinationEvidence,
    FaultEvidence,
    ProtectiveDeviceEvidence,
)
from src.protection_hierarchy import protection_coordination_assessments


class ProtectionPairEvidenceTests(unittest.TestCase):
    def _nested_graph(self):
        graph = make_radial_board_graph(board_id="MDB", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-01",
            sub_board_id="DB-01",
            description="Sub-board",
        )
        return add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Final load",
            parent_busbar_id="F-01:DB-01:busbar",
        )

    def _complete_evidence(self, upstream_rating=100.0, downstream_rating=32.0):
        return CoordinationEvidence(
            upstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="UP",
                rating_a=upstream_rating,
                settings_ref="UP settings",
                breaking_capacity_ka=25.0,
            ),
            downstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="DOWN",
                rating_a=downstream_rating,
                settings_ref="DOWN settings",
                breaking_capacity_ka=15.0,
            ),
            fault=FaultEvidence(prospective_fault_current_ka=8.0),
            cable=CableProtectionEvidence(
                cable_ref="CABLE-01",
                constraint_ref="cable constraint record",
                rule_basis_ref="rule basis record",
            ),
            manufacturer_coordination_ref="manufacturer coordination table reference",
        )

    def test_each_pair_reports_its_own_missing_evidence(self):
        graph = self._nested_graph()
        assessments = protection_coordination_assessments(graph)

        self.assertGreater(len(assessments), 1)
        for assessment in assessments:
            self.assertFalse(assessment.readiness.protection_ready_for_engineering_check)
            self.assertFalse(assessment.readiness.selectivity_ready_for_engineering_check)
            self.assertIn(
                "prospective fault current / fault-loop data at the protected point",
                assessment.missing_protection_evidence,
            )
            self.assertIn(
                "manufacturer selectivity/coordination table or verified time-current evidence",
                assessment.missing_selectivity_evidence,
            )

    def test_evidence_is_scoped_to_one_relationship_only(self):
        graph = self._nested_graph()
        relationships = protection_coordination_assessments(graph)
        target = relationships[0].relationship.pair_key

        assessments = protection_coordination_assessments(
            graph,
            evidence_by_pair={target: self._complete_evidence()},
        )
        target_assessment = next(item for item in assessments if item.relationship.pair_key == target)
        other_assessment = next(item for item in assessments if item.relationship.pair_key != target)

        self.assertTrue(target_assessment.readiness.protection_ready_for_engineering_check)
        self.assertTrue(target_assessment.readiness.selectivity_ready_for_engineering_check)
        self.assertFalse(other_assessment.readiness.protection_ready_for_engineering_check)
        self.assertFalse(other_assessment.readiness.selectivity_ready_for_engineering_check)

    def test_complete_pair_evidence_still_cannot_self_promote_to_verified(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        pair = ("incomer", "C-01:device")
        assessment = protection_coordination_assessments(
            graph,
            protection_check_requested=True,
            selectivity_check_requested=True,
            evidence_by_pair={pair: self._complete_evidence()},
        )[0]

        self.assertTrue(assessment.readiness.protection_ready_for_engineering_check)
        self.assertTrue(assessment.readiness.selectivity_ready_for_engineering_check)
        self.assertEqual(assessment.coordination.protection_status, "INSUFFICIENT DATA")
        self.assertEqual(assessment.coordination.selectivity_status, "INSUFFICIENT DATA")
        self.assertNotEqual(assessment.coordination.protection_status, "VERIFIED")
        self.assertNotEqual(assessment.coordination.selectivity_status, "VERIFIED")
        self.assertIn(
            "engineering selectivity verification has not been implemented/performed",
            assessment.coordination.missing_evidence,
        )

    def test_topology_ratings_are_not_silently_promoted_into_evidence(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        graph = replace(
            graph,
            nodes=tuple(
                replace(node, rating_a=100.0) if node.node_id == "incomer"
                else replace(node, rating_a=32.0) if node.node_id == "C-01:device"
                else node
                for node in graph.nodes
            ),
        )
        assessment = protection_coordination_assessments(graph)[0]

        self.assertEqual(assessment.upstream_rating_a, 100.0)
        self.assertEqual(assessment.downstream_rating_a, 32.0)
        self.assertFalse(assessment.readiness.selectivity_ready_for_engineering_check)
        self.assertIn(
            "upstream and downstream protective-device make/model/rating",
            assessment.missing_selectivity_evidence,
        )

    def test_conflicting_evidence_rating_fails_instead_of_silently_disagreeing(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        graph = replace(
            graph,
            nodes=tuple(
                replace(node, rating_a=100.0) if node.node_id == "incomer"
                else replace(node, rating_a=32.0) if node.node_id == "C-01:device"
                else node
                for node in graph.nodes
            ),
        )
        pair = ("incomer", "C-01:device")

        with self.assertRaisesRegex(ValueError, "disagrees with topology rating"):
            protection_coordination_assessments(
                graph,
                evidence_by_pair={pair: self._complete_evidence(upstream_rating=125.0)},
            )

    def test_evidence_for_unknown_relationship_is_rejected(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )

        with self.assertRaisesRegex(ValueError, "unknown protection relationship"):
            protection_coordination_assessments(
                graph,
                evidence_by_pair={("missing-upstream", "missing-downstream"): CoordinationEvidence()},
            )


if __name__ == "__main__":
    unittest.main()
