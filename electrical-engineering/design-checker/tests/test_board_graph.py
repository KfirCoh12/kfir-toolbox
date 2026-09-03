import unittest
from dataclasses import replace

from src.board_graph import (
    ElectricalNode,
    add_radial_circuit,
    add_sub_board_feeder,
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
        self.assertEqual(
            tuple(node.node_id for node in graph.ancestors_of("C-01:load")),
            ("C-01:cable", "C-01:device", "busbar", "incomer", "source"),
        )

    def test_graph_translates_to_existing_board_engine_without_duplicate_calculation_logic(self):
        graph = self._graph()
        request = board_plan_request_from_graph(graph)
        self.assertEqual(len(request.circuits), 2)
        self.assertEqual(request.phase_preferences[0].circuit_id, "C-01")
        self.assertEqual(request.phase_preferences[0].phase, "L2")
        self.assertEqual(calculate_board_plan(request).circuit_count, 2)

    def test_plan_enriches_existing_nodes_instead_of_rebuilding_hierarchy(self):
        graph = self._graph()
        result = calculate_board_plan(board_plan_request_from_graph(graph))
        enriched = enrich_graph_with_plan(graph, result)
        self.assertIsNotNone(enriched.node_by_id["C-02:device"].rating_a)
        self.assertIsNotNone(enriched.node_by_id["C-02:cable"].cable_mm2)
        self.assertEqual(enriched.node_by_id["C-02:load"].assigned_phase, "3P")
        self.assertEqual(enriched.node_by_id["C-02:device"].parent_id, "busbar")

    def test_single_phase_cable_candidate_is_enriched_without_losing_phase_assignment(self):
        graph = self._graph()
        result = calculate_board_plan(board_plan_request_from_graph(graph))
        enriched = enrich_graph_with_plan(graph, result)
        cable = enriched.node_by_id["C-01:cable"]
        self.assertEqual(cable.cable_mm2, 1.5)
        self.assertEqual(cable.cable_runs, 1)
        self.assertEqual(cable.scope_status, "SUPPORTED_SCOPE")
        self.assertNotIn("cable_dataset_phase_unsupported", cable.issue_codes)
        self.assertEqual(enriched.node_by_id["C-01:load"].assigned_phase, "L2")

    def test_sub_board_feeder_builds_complete_nested_radial_hierarchy(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        validate_board_graph(graph)
        self.assertEqual(graph.node_by_id["F-01:device"].parent_id, "busbar")
        self.assertEqual(graph.node_by_id["F-01:cable"].parent_id, "F-01:device")
        self.assertEqual(graph.node_by_id["F-01:DB-L1:board"].parent_id, "F-01:cable")
        self.assertEqual(graph.node_by_id["F-01:DB-L1:incomer"].parent_id, "F-01:DB-L1:board")
        self.assertEqual(graph.node_by_id["F-01:DB-L1:busbar"].parent_id, "F-01:DB-L1:incomer")
        self.assertEqual(graph.node_by_id["F-01:DB-L1:board"].board_ref, "DB-L1")

    def test_nested_sub_board_can_own_final_circuits(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Level 1 lighting",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        self.assertEqual(
            graph.node_by_id["L1-C01:device"].parent_id,
            "F-01:DB-L1:busbar",
        )
        self.assertIn(
            "F-01:DB-L1:board",
            tuple(node.node_id for node in graph.ancestors_of("L1-C01:load")),
        )

    def test_root_board_request_does_not_flatten_downstream_board_loads(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            circuit_id="C-ROOT",
            description="Root load",
            phase="three",
        )
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Downstream load",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        request = board_plan_request_from_graph(graph)
        self.assertEqual(tuple(c.circuit_id for c in request.circuits), ("C-ROOT",))

    def test_invalid_direct_component_relationship_is_rejected(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Board")
        bad = replace(
            graph,
            nodes=graph.nodes + (
                ElectricalNode("bad-load", "load", "Bad load", "busbar", circuit_id="BAD"),
            ),
        )
        with self.assertRaisesRegex(ValueError, "busbar cannot directly feed load"):
            validate_board_graph(bad)

    def test_duplicate_sub_board_identity_is_rejected(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        with self.assertRaisesRegex(ValueError, "already exists in hierarchy"):
            add_sub_board_feeder(
                graph,
                feeder_id="F-02",
                sub_board_id="DB-L1",
                description="Duplicate board",
            )

    def test_remove_circuit_removes_whole_branch_only(self):
        graph = remove_circuit(self._graph(), "C-01")
        self.assertNotIn("C-01:device", graph.node_by_id)
        self.assertNotIn("C-01:cable", graph.node_by_id)
        self.assertNotIn("C-01:load", graph.node_by_id)
        self.assertIn("C-02:load", graph.node_by_id)
        validate_board_graph(graph)

    def test_remove_sub_board_feeder_removes_entire_downstream_tree(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Nested load",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        graph = remove_circuit(graph, "F-01")
        self.assertNotIn("F-01:device", graph.node_by_id)
        self.assertNotIn("F-01:DB-L1:board", graph.node_by_id)
        self.assertNotIn("L1-C01:load", graph.node_by_id)
        validate_board_graph(graph)

    def test_duplicate_circuit_id_is_rejected(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Board")
        graph = add_radial_circuit(graph, circuit_id="C-01", description="Load A")
        with self.assertRaisesRegex(ValueError, "already exists"):
            add_radial_circuit(graph, circuit_id="C-01", description="Load B")


if __name__ == "__main__":
    unittest.main()
