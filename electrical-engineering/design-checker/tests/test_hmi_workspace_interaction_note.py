import unittest

from src.hmi_planner_workspace import _route_graph_nodes
from src.board_graph import add_radial_circuit, make_radial_board_graph


class HmiWorkspaceInteractionTests(unittest.TestCase):
    def test_route_focus_includes_circuit_and_upstream_ancestors(self):
        graph = make_radial_board_graph(
            board_id="DB-01",
            description="Test board",
            line_to_line_voltage_v=400.0,
            line_to_neutral_voltage_v=230.0,
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Test load",
            load_kw=10.0,
            phase="three",
            power_factor=0.9,
            demand_factor=1.0,
            material="copper",
        )

        route = set(_route_graph_nodes(graph, None, "C-01"))
        circuit_nodes = {node.node_id for node in graph.nodes if node.circuit_id == "C-01"}

        self.assertTrue(circuit_nodes.issubset(route))
        self.assertTrue(any(graph.node_by_id[node_id].kind == "source" for node_id in route))
        self.assertTrue(any(graph.node_by_id[node_id].kind == "busbar" for node_id in route))


if __name__ == "__main__":
    unittest.main()
