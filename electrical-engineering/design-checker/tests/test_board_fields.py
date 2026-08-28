import unittest

from src.board_graph import (
    add_field_feeder,
    add_radial_circuit,
    board_plan_request_from_graph,
    make_radial_board_graph,
    remove_circuit,
    validate_board_graph,
)


class BoardFieldTests(unittest.TestCase):
    def test_field_builds_lightweight_distribution_hierarchy(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-LTG",
            field_id="LTG",
            description="Lighting field",
        )
        validate_board_graph(graph)
        self.assertEqual(graph.node_by_id["F-LTG:device"].parent_id, "busbar")
        self.assertEqual(graph.node_by_id["F-LTG:cable"].parent_id, "F-LTG:device")
        self.assertEqual(graph.node_by_id["F-LTG:LTG:field"].parent_id, "F-LTG:cable")
        self.assertEqual(graph.node_by_id["F-LTG:LTG:field"].field_ref, "LTG")
        self.assertEqual(graph.node_by_id["F-LTG:LTG:busbar"].parent_id, "F-LTG:LTG:field")

    def test_field_can_own_multiple_final_circuits(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-LTG",
            field_id="LTG",
            description="Lighting field",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-01",
            description="Lighting zone A",
            load_kw=1.2,
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-02",
            description="Lighting zone B",
            load_kw=1.4,
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        self.assertEqual(graph.node_by_id["LTG-01:device"].parent_id, "F-LTG:LTG:busbar")
        self.assertEqual(graph.node_by_id["LTG-02:device"].parent_id, "F-LTG:LTG:busbar")

    def test_field_child_loads_remain_in_root_board_calculation_boundary(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-LTG",
            field_id="LTG",
            description="Lighting field",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-01",
            description="Lighting zone A",
            load_kw=1.2,
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-02",
            description="Lighting zone B",
            load_kw=1.4,
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        request = board_plan_request_from_graph(graph)
        self.assertEqual(
            tuple(c.circuit_id for c in request.circuits),
            ("LTG-01", "LTG-02"),
        )

    def test_duplicate_field_identity_is_rejected(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-LTG",
            field_id="LTG",
            description="Lighting field",
        )
        with self.assertRaisesRegex(ValueError, "already exists in hierarchy"):
            add_field_feeder(
                graph,
                feeder_id="F-LTG-2",
                field_id="LTG",
                description="Duplicate field",
            )

    def test_removing_field_feeder_removes_all_child_circuits(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-LTG",
            field_id="LTG",
            description="Lighting field",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-01",
            description="Lighting zone A",
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        graph = remove_circuit(graph, "F-LTG")
        self.assertNotIn("F-LTG:LTG:field", graph.node_by_id)
        self.assertNotIn("LTG-01:load", graph.node_by_id)
        validate_board_graph(graph)


if __name__ == "__main__":
    unittest.main()
