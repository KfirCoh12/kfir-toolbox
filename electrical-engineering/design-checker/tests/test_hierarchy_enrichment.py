import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_enrichment import enrich_graph_with_hierarchy_plan
from src.hierarchy_planner import calculate_board_hierarchy


class HierarchyEnrichmentTests(unittest.TestCase):
    def _graph(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_radial_circuit(
            graph,
            circuit_id="C-ROOT",
            description="Root load",
            load_kw=6.0,
            phase="three",
        )
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Child board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-CHILD",
            description="Child load",
            load_kw=18.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        return graph

    def test_enrichment_applies_final_circuits_board_incomers_and_feeder_breaker(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        enriched = enrich_graph_with_hierarchy_plan(graph, hierarchy)
        by_id = enriched.node_by_id

        root_row = hierarchy.plans_by_board_id["DB-01"].schedule_rows[0]
        child_row = hierarchy.plans_by_board_id["DB-02"].schedule_rows[0]
        rollup = hierarchy.feeder_rollups[0]

        self.assertEqual(by_id["C-ROOT:device"].rating_a, root_row.breaker_a)
        self.assertEqual(by_id["C-ROOT:cable"].cable_mm2, root_row.cable_mm2)
        self.assertEqual(by_id["C-CHILD:device"].rating_a, child_row.breaker_a)
        self.assertEqual(by_id["C-CHILD:cable"].cable_mm2, child_row.cable_mm2)

        self.assertEqual(
            by_id["incomer"].rating_a,
            hierarchy.plans_by_board_id["DB-01"].incomer_candidate.breaker_rating_a,
        )
        self.assertEqual(
            by_id["DBF-01:DB-02:incomer"].rating_a,
            hierarchy.plans_by_board_id["DB-02"].incomer_candidate.breaker_rating_a,
        )
        self.assertIn("BOARD_INCOMER_PROVISIONAL", by_id["incomer"].issue_codes)
        self.assertEqual(by_id["DBF-01:device"].rating_a, rollup.breaker_candidate_a)
        self.assertIn("SUB_BOARD_FEEDER_PROVISIONAL", by_id["DBF-01:device"].issue_codes)

    def test_sub_board_feeder_cable_remains_unsized(self):
        graph = self._graph()
        enriched = enrich_graph_with_hierarchy_plan(graph, calculate_board_hierarchy(graph))
        feeder_cable = enriched.node_by_id["DBF-01:cable"]
        self.assertIsNone(feeder_cable.cable_mm2)
        self.assertIsNone(feeder_cable.cable_runs)

    def test_parent_with_only_child_demand_still_gets_incomer_candidate(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Child board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-CHILD",
            description="Child load",
            load_kw=10.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        hierarchy = calculate_board_hierarchy(graph)
        enriched = enrich_graph_with_hierarchy_plan(graph, hierarchy)
        self.assertEqual(
            enriched.node_by_id["incomer"].rating_a,
            hierarchy.root.plan.incomer_candidate.breaker_rating_a,
        )

    def test_empty_board_does_not_invent_incomer_or_feeder_rating(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Empty child board",
        )
        hierarchy = calculate_board_hierarchy(graph)
        enriched = enrich_graph_with_hierarchy_plan(graph, hierarchy)
        self.assertIsNone(enriched.node_by_id["incomer"].rating_a)
        self.assertIsNone(enriched.node_by_id["DBF-01:DB-02:incomer"].rating_a)
        self.assertIsNone(enriched.node_by_id["DBF-01:device"].rating_a)
        self.assertNotIn(
            "SUB_BOARD_FEEDER_PROVISIONAL",
            enriched.node_by_id["DBF-01:device"].issue_codes,
        )

    def test_rejects_result_from_different_graph_hierarchy(self):
        graph = self._graph()
        other = make_radial_board_graph(board_id="DB-X", description="Other")
        hierarchy = calculate_board_hierarchy(other)
        with self.assertRaisesRegex(ValueError, "do not match graph board hierarchy"):
            enrich_graph_with_hierarchy_plan(graph, hierarchy)


if __name__ == "__main__":
    unittest.main()
