import unittest
from dataclasses import replace

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.protection_hierarchy import (
    protection_chain_for_node,
    protection_chains,
    protection_coordination_assessments,
    protection_relationships,
)


class ProtectionHierarchyTests(unittest.TestCase):
    def test_outgoing_protection_is_related_to_main_incomer_automatically(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Lighting",
        )
        relationships = protection_relationships(graph)
        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertEqual(relationship.upstream_node_id, "incomer")
        self.assertEqual(relationship.downstream_node_id, "C-01:device")
        self.assertEqual(relationship.downstream_circuit_id, "C-01")

    def test_each_outgoing_device_gets_its_own_relationship(self):
        graph = make_radial_board_graph(board_id="DB-02", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Lighting")
        graph = add_radial_circuit(graph, circuit_id="C-02", description="Sockets")
        relationships = protection_relationships(graph)
        self.assertEqual(
            {(r.upstream_node_id, r.downstream_node_id) for r in relationships},
            {("incomer", "C-01:device"), ("incomer", "C-02:device")},
        )

    def test_sub_board_incomer_uses_feeder_device_as_nearest_upstream_device(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        relationships = protection_relationships(graph)
        pairs = {(r.upstream_node_id, r.downstream_node_id) for r in relationships}
        self.assertIn(("incomer", "F-01:device"), pairs)
        self.assertIn(("F-01:device", "F-01:DB-L1:incomer"), pairs)

    def test_downstream_final_device_uses_sub_board_incomer_not_root_incomer(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Lighting",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        relationships = protection_relationships(graph)
        downstream = next(r for r in relationships if r.downstream_node_id == "L1-C01:device")
        self.assertEqual(downstream.upstream_node_id, "F-01:DB-L1:incomer")
        self.assertEqual(downstream.downstream_circuit_id, "L1-C01")

    def _nested_graph(self):
        graph = make_radial_board_graph(board_id="MDB", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-02",
            sub_board_id="DB-L2",
            description="Level 2 board",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        return add_radial_circuit(
            graph,
            circuit_id="L2-C01",
            description="Final load",
            parent_busbar_id="F-02:DB-L2:busbar",
        )

    def test_complete_chain_preserves_every_protection_layer_in_order(self):
        graph = self._nested_graph()
        chain = protection_chain_for_node(graph, "L2-C01:device")
        self.assertEqual(
            chain.node_ids,
            (
                "incomer",
                "F-01:device",
                "F-01:DB-L1:incomer",
                "F-02:device",
                "F-02:DB-L2:incomer",
                "L2-C01:device",
            ),
        )
        self.assertEqual(chain.endpoint_circuit_id, "L2-C01")
        self.assertFalse(chain.ratings_complete)

    def test_terminal_chains_return_one_end_to_end_path_per_protection_branch(self):
        graph = self._nested_graph()
        graph = add_radial_circuit(
            graph,
            circuit_id="ROOT-C01",
            description="Root load",
        )
        chains = protection_chains(graph)
        self.assertEqual(
            {chain.endpoint_node_id for chain in chains},
            {"L2-C01:device", "ROOT-C01:device"},
        )
        self.assertEqual(
            next(chain for chain in chains if chain.endpoint_node_id == "ROOT-C01:device").node_ids,
            ("incomer", "ROOT-C01:device"),
        )

    def test_all_chains_can_include_intermediate_protective_devices(self):
        graph = self._nested_graph()
        endpoint_ids = {chain.endpoint_node_id for chain in protection_chains(graph, terminal_only=False)}
        self.assertIn("F-01:device", endpoint_ids)
        self.assertIn("F-01:DB-L1:incomer", endpoint_ids)
        self.assertIn("F-02:device", endpoint_ids)
        self.assertIn("L2-C01:device", endpoint_ids)

    def test_relationship_and_chain_expose_ratings_without_claiming_coordination(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        graph = replace(
            graph,
            nodes=tuple(
                replace(node, rating_a=63.0) if node.node_id == "incomer"
                else replace(node, rating_a=16.0) if node.node_id == "C-01:device"
                else node
                for node in graph.nodes
            ),
        )
        relationship = protection_relationships(graph)[0]
        self.assertEqual(relationship.upstream_rating_a, 63.0)
        self.assertEqual(relationship.downstream_rating_a, 16.0)
        chain = protection_chain_for_node(graph, "C-01:device")
        self.assertEqual(tuple(device.rating_a for device in chain.devices), (63.0, 16.0))
        self.assertTrue(chain.ratings_complete)

    def test_pair_coordination_defaults_to_not_checked_even_when_ratings_are_ordered(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        graph = replace(
            graph,
            nodes=tuple(
                replace(node, rating_a=63.0) if node.node_id == "incomer"
                else replace(node, rating_a=16.0) if node.node_id == "C-01:device"
                else node
                for node in graph.nodes
            ),
        )
        assessment = protection_coordination_assessments(graph)[0]
        self.assertEqual(assessment.upstream_rating_a, 63.0)
        self.assertEqual(assessment.downstream_rating_a, 16.0)
        self.assertEqual(assessment.coordination.protection_status, "NOT CHECKED")
        self.assertEqual(assessment.coordination.selectivity_status, "NOT CHECKED")

    def test_requested_pair_selectivity_is_insufficient_without_real_evidence(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        graph = replace(
            graph,
            nodes=tuple(
                replace(node, rating_a=100.0) if node.node_id == "incomer"
                else replace(node, rating_a=10.0) if node.node_id == "C-01:device"
                else node
                for node in graph.nodes
            ),
        )
        assessment = protection_coordination_assessments(
            graph,
            selectivity_check_requested=True,
        )[0]
        self.assertEqual(assessment.coordination.protection_status, "NOT CHECKED")
        self.assertEqual(assessment.coordination.selectivity_status, "INSUFFICIENT DATA")
        self.assertNotEqual(assessment.coordination.selectivity_status, "VERIFIED")
        self.assertIn(
            "manufacturer selectivity/coordination table or verified time-current evidence",
            assessment.coordination.missing_evidence,
        )

    def test_missing_ratings_do_not_block_topology_but_cannot_verify_coordination(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        assessment = protection_coordination_assessments(
            graph,
            protection_check_requested=True,
            selectivity_check_requested=True,
        )[0]
        self.assertIsNone(assessment.upstream_rating_a)
        self.assertIsNone(assessment.downstream_rating_a)
        self.assertEqual(assessment.coordination.protection_status, "INSUFFICIENT DATA")
        self.assertEqual(assessment.coordination.selectivity_status, "INSUFFICIENT DATA")

    def test_nested_chain_produces_one_coordination_assessment_per_adjacent_pair(self):
        graph = self._nested_graph()
        assessments = protection_coordination_assessments(graph)
        pairs = {
            (
                assessment.relationship.upstream_node_id,
                assessment.relationship.downstream_node_id,
            )
            for assessment in assessments
        }
        self.assertEqual(
            pairs,
            {
                ("incomer", "F-01:device"),
                ("F-01:device", "F-01:DB-L1:incomer"),
                ("F-01:DB-L1:incomer", "F-02:device"),
                ("F-02:device", "F-02:DB-L2:incomer"),
                ("F-02:DB-L2:incomer", "L2-C01:device"),
            },
        )

    def test_chain_rejects_non_protective_or_unknown_endpoint(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            circuit_id="C-01",
            description="Load",
        )
        with self.assertRaisesRegex(ValueError, "not a protective device"):
            protection_chain_for_node(graph, "C-01:load")
        with self.assertRaisesRegex(ValueError, "unknown node"):
            protection_chain_for_node(graph, "missing")


if __name__ == "__main__":
    unittest.main()
