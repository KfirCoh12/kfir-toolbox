import unittest

from src.board_graph import add_radial_circuit, make_radial_board_graph
from src.single_line_svg import render_board_graph_svg


class SingleLineSvgTests(unittest.TestCase):
    def test_renderer_shows_minimal_board_before_any_circuit_exists(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Board")
        svg = render_board_graph_svg(graph)
        self.assertIn("Supply", svg)
        self.assertIn("Main incomer", svg)
        self.assertIn("Main busbar", svg)
        self.assertIn("rating pending", svg)

    def test_minimal_board_is_centered_in_minimum_viewport(self):
        graph = make_radial_board_graph(board_id="DB-CENTER", description="Board")
        svg = render_board_graph_svg(graph)
        self.assertIn('viewBox="0 0 760', svg)
        self.assertIn('x="380.0"', svg)

    def test_renderer_updates_from_draft_circuit_inputs_without_calculation(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-02", description="Board"),
            circuit_id="C-01",
            description="Lighting",
            load_kw=2.5,
            phase="single",
        )
        svg = render_board_graph_svg(graph)
        self.assertIn("C-01 protection", svg)
        self.assertIn("C-01 cable", svg)
        self.assertIn("Lighting", svg)
        self.assertIn("2.5 kW", svg)
        self.assertIn("1P", svg)
        self.assertIn("cable pending", svg)
        self.assertIn('x="380.0"', svg)

    def test_multiple_branches_expand_around_common_center(self):
        graph = make_radial_board_graph(board_id="DB-04", description="Board")
        for index in range(3):
            graph = add_radial_circuit(
                graph,
                circuit_id=f"C-{index + 1:02d}",
                description=f"Load {index + 1}",
                load_kw=2,
                phase="single",
            )
        svg = render_board_graph_svg(graph)
        self.assertIn('x="195.0"', svg)
        self.assertIn('x="380.0"', svg)
        self.assertIn('x="565.0"', svg)

    def test_renderer_escapes_user_labels(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-03", description="Board"),
            circuit_id="C-01",
            description="AHU <North & East>",
        )
        svg = render_board_graph_svg(graph)
        self.assertIn("AHU &lt;North &amp; East&gt;", svg)
        self.assertNotIn("AHU <North & East>", svg)


if __name__ == "__main__":
    unittest.main()
