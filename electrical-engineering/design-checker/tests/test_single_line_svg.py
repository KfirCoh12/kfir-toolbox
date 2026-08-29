import unittest

from src.board_graph import (
    add_field_feeder,
    add_radial_circuit,
    add_sub_board_feeder,
    make_radial_board_graph,
)
from src.single_line_svg import render_board_graph_svg


class SingleLineSvgTests(unittest.TestCase):
    def test_renderer_shows_minimal_board_before_any_circuit_exists(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Board")
        svg = render_board_graph_svg(graph)
        self.assertIn("Supply", svg)
        self.assertIn("Main incomer", svg)
        self.assertIn("Main busbar", svg)
        self.assertIn("rating pending", svg)

    def test_minimal_board_is_centered_and_fit_to_view(self):
        graph = make_radial_board_graph(board_id="DB-C", description="Centered board")
        svg = render_board_graph_svg(graph)
        self.assertIn('viewBox="0 0 820 ', svg)
        self.assertIn('x="410.0"', svg)
        self.assertIn('height="100%"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)

    def test_renderer_collapses_protection_and_cable_into_final_branch_box(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-02", description="Board"),
            circuit_id="C-01",
            description="Lighting",
            load_kw=2.5,
            phase="single",
        )
        svg = render_board_graph_svg(graph)
        self.assertIn("C-01 · Lighting", svg)
        self.assertIn("2.5 kW", svg)
        self.assertIn("1P", svg)
        self.assertIn("protection pending", svg)
        self.assertIn("cable pending", svg)
        self.assertNotIn(">C-01 protection<", svg)
        self.assertNotIn(">C-01 cable<", svg)

    def test_manual_outlet_basis_is_shown_without_fake_kw_load(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-M", description="Manual board"),
            circuit_id="C-32",
            description="Known outlet",
            load_kw=None,
            phase="three",
            display_detail="Manual · 32 A outlet",
        )
        svg = render_board_graph_svg(graph)
        self.assertIn("Manual · 32 A outlet", svg)
        self.assertIn("3P", svg)
        self.assertNotIn("None kW", svg)

    def test_renderer_expands_field_and_child_circuit_with_compact_branch_boxes(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-F", description="Field board"),
            feeder_id="F-01",
            field_id="LTG",
            description="Lighting field",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-01",
            description="Lighting zone A",
            load_kw=1.2,
            parent_busbar_id="F-01:LTG:busbar",
        )
        svg = render_board_graph_svg(graph)
        self.assertIn("Lighting field", svg)
        self.assertIn("LTG · grouped circuits", svg)
        self.assertIn("F-01 · protection pending · cable pending", svg)
        self.assertIn("LTG busbar", svg)
        self.assertIn("LTG-01 · Lighting zone A", svg)
        self.assertIn("group-green", svg)
        self.assertNotIn(">F-01 field protection<", svg)

    def test_renderer_collapses_downstream_incomer_into_sub_board_box(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Downstream board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-07",
            description="Sub-board load",
            load_kw=1.0,
            phase="single",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        svg = render_board_graph_svg(graph)
        self.assertIn("Downstream board", svg)
        self.assertIn("DB-02 · incomer rating pending", svg)
        self.assertIn("DBF-01 · protection pending · cable pending", svg)
        self.assertIn("DB-02 busbar", svg)
        self.assertIn("C-07 · Sub-board load", svg)
        self.assertNotIn(">DB-02 incomer<", svg)
        self.assertIn("Main incomer", svg)

    def test_renderer_can_highlight_selected_visible_object(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="DB-S", description="Selected board"),
            circuit_id="C-01",
            description="Selected load",
        )
        svg = render_board_graph_svg(graph, ("C-01:load",))
        self.assertIn("node normal selected", svg)

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
