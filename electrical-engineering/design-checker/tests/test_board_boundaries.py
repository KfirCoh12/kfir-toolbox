import unittest

from src.board_boundaries import calculation_boundaries_from_graph
from src.board_graph import (
    add_radial_circuit,
    add_sub_board_feeder,
    make_radial_board_graph,
)
from src.board_planner import calculate_board_plan


class BoardCalculationBoundaryTests(unittest.TestCase):
    def test_root_and_sub_board_get_separate_requests(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            circuit_id="C-ROOT",
            description="Root load",
            phase="three",
            load_kw=12.0,
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
            description="Level 1 lighting",
            phase="single",
            load_kw=2.0,
            phase_preference="L3",
            parent_busbar_id="F-01:DB-L1:busbar",
        )

        boundaries = calculation_boundaries_from_graph(graph)
        self.assertEqual(tuple(b.board_id for b in boundaries), ("MDB", "DB-L1"))
        self.assertEqual(tuple(b.status for b in boundaries), ("READY", "READY"))

        root, child = boundaries
        self.assertEqual(tuple(c.circuit_id for c in root.request.circuits), ("C-ROOT",))
        self.assertEqual(tuple(c.circuit_id for c in child.request.circuits), ("L1-C01",))
        self.assertEqual(child.description, "Level 1 board")
        self.assertEqual(child.feeder_circuit_id, "F-01")
        self.assertEqual(child.busbar_node_id, "F-01:DB-L1:busbar")
        self.assertEqual(child.phase_preferences[0].phase if hasattr(child, "phase_preferences") else child.request.phase_preferences[0].phase, "L3")

    def test_downstream_load_is_not_flattened_into_parent_request(self):
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

        root, child = calculation_boundaries_from_graph(graph)
        self.assertEqual(tuple(c.circuit_id for c in root.request.circuits), ("C-ROOT",))
        self.assertEqual(tuple(c.circuit_id for c in child.request.circuits), ("L1-C01",))
        self.assertNotIn("F-01", tuple(c.circuit_id for c in root.request.circuits))

    def test_each_ready_boundary_can_run_through_existing_board_engine(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Three phase child load",
            phase="three",
            load_kw=18.0,
            parent_busbar_id="F-01:DB-L1:busbar",
        )

        root, child = calculation_boundaries_from_graph(graph)
        self.assertEqual(root.status, "NO_FINAL_LOADS")
        self.assertIsNone(root.request)
        self.assertEqual(child.status, "READY")
        result = calculate_board_plan(child.request)
        self.assertEqual(result.request.board_id, "DB-L1")
        self.assertEqual(result.circuit_count, 1)

    def test_empty_nested_board_remains_explicit_boundary(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        boundaries = calculation_boundaries_from_graph(graph)
        self.assertEqual(len(boundaries), 2)
        self.assertEqual(boundaries[0].status, "NO_FINAL_LOADS")
        self.assertEqual(boundaries[1].status, "NO_FINAL_LOADS")
        self.assertIsNone(boundaries[1].request)
        self.assertEqual(boundaries[1].anchor_node_id, "F-01:DB-L1:board")

    def test_three_level_hierarchy_keeps_board_ownership_local(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Level 1 load",
            phase="three",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-02",
            sub_board_id="DB-L2",
            description="Level 2 board",
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L2-C01",
            description="Level 2 load",
            phase="three",
            parent_busbar_id="F-02:DB-L2:busbar",
        )

        boundaries = calculation_boundaries_from_graph(graph)
        self.assertEqual(tuple(b.board_id for b in boundaries), ("MDB", "DB-L1", "DB-L2"))
        self.assertEqual(boundaries[0].status, "NO_FINAL_LOADS")
        self.assertEqual(tuple(c.circuit_id for c in boundaries[1].request.circuits), ("L1-C01",))
        self.assertEqual(tuple(c.circuit_id for c in boundaries[2].request.circuits), ("L2-C01",))
        self.assertEqual(boundaries[2].feeder_circuit_id, "F-02")


if __name__ == "__main__":
    unittest.main()
