import re
import unittest

from src.board_graph import add_radial_circuit, make_radial_board_graph
from src.hmi_single_line import render_hmi_single_line_svg
from src.sample_boards import office_700m2_150_people_board
from src.working_board_plan import calculate_working_board


class HmiSingleLineTests(unittest.TestCase):
    def test_renderer_uses_line_symbols_and_context_labels(self):
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
        svg = render_hmi_single_line_svg(graph)
        self.assertIn("<svg", svg)
        self.assertIn("Main busbar", svg)
        self.assertIn("C-01 protection", svg)
        self.assertIn("Test load", svg)
        self.assertIn("<rect", svg)
        self.assertIn("<line", svg)

    def test_selected_nodes_use_accent_without_changing_graph(self):
        graph = make_radial_board_graph(
            board_id="DB-01",
            description="Test board",
            line_to_line_voltage_v=400.0,
            line_to_neutral_voltage_v=230.0,
        )
        svg = render_hmi_single_line_svg(graph, selected_node_ids=("incomer",))
        self.assertIn("#39aef7", svg)

    def test_selected_circuit_path_uses_glow_and_accent_geometry(self):
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
        selected = tuple(node.node_id for node in graph.nodes if node.circuit_id == "C-01")
        svg = render_hmi_single_line_svg(graph, selected_node_ids=selected)
        self.assertIn("#39aef7", svg)
        self.assertIn('filter="url(#glow)"', svg)
        self.assertIn("C-01 protection", svg)

    def test_large_office_board_keeps_readable_intrinsic_width_and_full_field_paths(self):
        calculated = calculate_working_board(office_700m2_150_people_board())
        graph = calculated.graph
        root_selected = tuple(
            node.node_id
            for node in graph.nodes
            if node.kind in ("incomer", "busbar") and (node.board_ref or graph.board_id) == graph.board_id
        )
        svg = render_hmi_single_line_svg(graph, selected_node_ids=root_selected)

        width_match = re.search(r'<svg[^>]* width="(\d+)"', svg)
        self.assertIsNotNone(width_match)
        self.assertGreater(int(width_match.group(1)), 3000)
        self.assertIn("FIELD-GP busbar", svg)
        self.assertIn("GP-01 protection", svg)
        self.assertIn("Open-office socket zone 01", svg)
        self.assertIn("rotate(-90", svg)
        self.assertIn('stroke-width="3.2"', svg)
        self.assertIn('stroke="#9bb0c8"', svg)

    def test_large_office_board_circuit_focus_hides_unrelated_siblings_and_keeps_field_busbar(self):
        calculated = calculate_working_board(office_700m2_150_people_board())
        graph = calculated.graph
        selected_ids = {node.node_id for node in graph.nodes if node.circuit_id == "GP-01"}
        for node_id in tuple(selected_ids):
            selected_ids.update(node.node_id for node in graph.ancestors_of(node_id))

        svg = render_hmi_single_line_svg(graph, selected_node_ids=tuple(selected_ids))
        self.assertIn("FIELD-GP busbar", svg)
        self.assertIn("GP-01 protection", svg)
        self.assertNotIn("GP-02 protection", svg)
        self.assertIn('filter="url(#glow)"', svg)
        self.assertIn('stroke-width="3.2"', svg)


if __name__ == "__main__":
    unittest.main()
