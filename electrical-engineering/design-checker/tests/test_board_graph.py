import unittest

from src.board_graph import (
    add_radial_circuit,
    board_plan_request_from_graph,
    enrich_graph_with_plan,
    make_radial_board_graph,
    remove_circuit,
    validate_board_graph,
)
from src.board_planner import calculate_board_plan


class BoardGraphTests(unittest.TestCase):
    def _graph(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Office board")
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Lighting",
            load_kw=2.0,
            phase="single",
            phase_preference="L2",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-02",
            description="AHU",
            load_kw=12.0,
            phase="three",
        )
        return graph

    def test_graph_has_real_component_hierarchy(self):
        graph = self._graph()
        validate_board_graph(graph)
        self.assertEqual(graph.root_nodes[0].kind, "source")
        self.assertEqual(graph.node_by_id["incomer"].parent_id, "source")
        self.assertEqual(graph.node_by_id["busbar"].parent_id, "incomer")
        self.assertEqual(graph.node_by_id["C-01:device"].parent_id, "busbar")
        self.assertEqual(graph.node_by_id["C-01:cable"].parent_id, "C-01:device")
        self.assertEqual(graph.node_by_id["C-01:load"].parent_id, "C-01:cable")
        ancestors = graph.ancestors_of("C-01:load")
        self.assertEqual(
            tuple(node.node_id for node in ancestors),
            ("C-01:cable", "C-01:device", "busbar", "incomer", "source"),
        )

    def test_graph_translates_to_existing_board_engine_without_duplicate_calculation_logic(self):
        graph = self._graph()
        request = board_plan_request_from_graph(graph)
        self.assertEqual(len(request.circuits), 2)
        self.assertEqual(request.phase_preferences[0].circuit_id, "C-01")
        self.assertEqual(request.phase_preferences[0].phase, "L2")
        result = calculate_board_plan(request)
        self.assertEqual(result.circuit_count, 2)

    def test_plan_enriches_existing_nodes_instead_of_rebuilding_hierarchy(self):
        graph = self._graph()
        result = calculate_board_plan(board_plan_request_from_graph(graph))
        enriched = enrich_graph_with_plan(graph, result)
        device = enriched.node_by_id["C-02:device"]
        cable = enriched.node_by_id["C-02:cable"]
        load = enriched.node_by_id["C-02:load"]
        self.assertIsNotNone(device.rating_a)
        self.assertIsNotNone(cable.cable_mm2)
        self.assertEqual(load.assigned_phase, "3P")
        self.assertEqual(device.parent_id, "busbar")
        self.assertEqual(cable.parent_id, "C-02:device")

    def test_single_phase_unsupported_cable_stays_unverified_after_enrichment(self):
        graph = self._graph()
        result = calculate_board_plan(board_plan_request_from_graph(graph))
        enriched = enrich_graph_with_plan(graph, result)
        cable = enriched.node_by_id["C-01:cable"]
        self.assertIsNone(cable.cable_mm2)
        self.assertEqual(cable.scope_status, "PARTIAL_SCOPE")
        self.assertIn("cable_dataset_phase_unsupported", cable.issue_codes)
        self.assertEqual(enriched.node_by_id["C-01:load"].assigned_phase, "L2")

    def test_remove_circuit_removes_whole_branch_only(self):
        graph = remove_circuit(self._graph(), "C-01")
        self.assertNotIn("C-01:device", graph.node_by_id)
        self.assertNotIn("C-01:cable", graph.node_by_id)
        self.assertNotIn("C-01:load", graph.node_by_id)
        self.assertIn("C-02:load", graph.node_by_id)
        validate_board_graph(graph)

    def test_duplicate_circuit_id_is_rejected(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Load A")
        with self.assertRaisesRegex(ValueError, "already exists"):
            add_radial_circuit(graph, circuit_id="C-01", description="Load B")


if __name__ == "__main__":
    unittest.main()
