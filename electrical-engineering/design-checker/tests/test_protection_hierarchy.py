import unittest

from src.board_graph import add_radial_circuit, make_radial_board_graph
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

    def test_each_outgoing_device_gets_its_own_selectivity_relationship(self):
        graph = make_radial_board_graph(board_id="DB-02", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Lighting")
        graph = add_radial_circuit(graph, circuit_id="C-02", description="Sockets")
        relationships = protection_relationships(graph)
        self.assertEqual(
            {(r.upstream_node_id, r.downstream_node_id) for r in relationships},
            {("incomer", "C-01:device"), ("incomer", "C-02:device")},
        )


if __name__ == "__main__":
    unittest.main()
