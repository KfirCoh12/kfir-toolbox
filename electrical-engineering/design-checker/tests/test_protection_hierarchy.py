import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.protection_hierarchy import protection_relationships


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


if __name__ == "__main__":
    unittest.main()
