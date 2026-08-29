import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_display import enrich_graph_with_hierarchy_plan
from src.hierarchy_planner import calculate_board_hierarchy
from src.single_line_svg import render_board_graph_svg


class HierarchyDisplayTests(unittest.TestCase):
    def test_sub_board_plan_enriches_incomer_feeder_and_child_branch(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Lighting board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Child load",
            load_kw=2.0,
            phase="single",
            phase_preference="L1",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

        hierarchy = calculate_board_hierarchy(graph)
        enriched = enrich_graph_with_hierarchy_plan(graph, hierarchy)
        by_id = enriched.node_by_id
        child_plan = hierarchy.plans_by_board_id["DB-02"]
        feeder = hierarchy.feeder_rollups[0]

        self.assertEqual(
            by_id["DBF-01:DB-02:incomer"].rating_a,
            child_plan.incomer_candidate.breaker_rating_a,
        )
        self.assertEqual(by_id["DBF-01:device"].rating_a, feeder.breaker_candidate_a)
        self.assertIsNone(by_id["DBF-01:cable"].cable_mm2)
        self.assertEqual(
            by_id["C-01:device"].rating_a,
            child_plan.schedule_rows[0].breaker_a,
        )
        self.assertEqual(by_id["C-01:load"].assigned_phase, "L1")
        self.assertIn("A max", by_id["DBF-01:DB-02:board"].display_detail)

    def test_enriched_sub_board_svg_no_longer_shows_rating_pending_when_calculated(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Sub-board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Child load",
            load_kw=3.0,
            phase="single",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

        enriched = enrich_graph_with_hierarchy_plan(
            graph,
            calculate_board_hierarchy(graph),
        )
        svg = render_board_graph_svg(enriched)
        self.assertIn("A incomer", svg)
        self.assertIn("A max", svg)
        self.assertNotIn("DB-02 · incomer rating pending", svg)
        self.assertIn("DBF-01 ·", svg)
        self.assertIn("protection", svg)


if __name__ == "__main__":
    unittest.main()
