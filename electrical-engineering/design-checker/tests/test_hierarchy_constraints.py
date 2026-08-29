import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_constraints import BreakerRatingConstraint, assess_breaker_constraints
from src.hierarchy_planner import calculate_board_hierarchy


class HierarchyConstraintTests(unittest.TestCase):
    def _graph(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Sub-board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-ROOT",
            description="Root load",
            load_kw=18.0,
            phase="three",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-CHILD",
            description="Child load",
            load_kw=9.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        return graph

    def test_incomer_constraint_compares_against_full_board_demand(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        assessment = assess_breaker_constraints(
            graph,
            hierarchy,
            (BreakerRatingConstraint("incomer", 63.0, "Existing main breaker"),),
        )[0]
        self.assertEqual(assessment.kind, "INCOMER")
        self.assertEqual(assessment.board_id, "DB-01")
        self.assertEqual(assessment.status, "WITHIN_RATING")
        self.assertGreater(assessment.required_current_a, 0)
        self.assertGreaterEqual(assessment.margin_a, 0)
        self.assertIn("selectivity", assessment.limitation)

    def test_sub_board_feeder_constraint_uses_child_board_rollup(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        rollup = hierarchy.feeder_rollups[0]
        assessment = assess_breaker_constraints(
            graph,
            hierarchy,
            (BreakerRatingConstraint("DBF-01:device", 32.0, "Known feeder breaker"),),
        )[0]
        self.assertEqual(assessment.kind, "SUB_BOARD_FEEDER")
        self.assertEqual(assessment.circuit_id, "DBF-01")
        self.assertAlmostEqual(assessment.required_current_a, rollup.required_current_a)
        self.assertEqual(assessment.board_id, "DB-01")

    def test_final_circuit_constraint_uses_branch_design_current(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        child_plan = hierarchy.plans_by_board_id["DB-02"]
        child_current = child_plan.circuits[0].design_current_a
        assessment = assess_breaker_constraints(
            graph,
            hierarchy,
            (BreakerRatingConstraint("C-CHILD:device", 20.0, "Existing branch breaker"),),
        )[0]
        self.assertEqual(assessment.kind, "FINAL_CIRCUIT")
        self.assertAlmostEqual(assessment.required_current_a, child_current)
        self.assertEqual(assessment.board_id, "DB-02")

    def test_undersized_declared_rating_is_reported_without_coordination_claim(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        assessment = assess_breaker_constraints(
            graph,
            hierarchy,
            (BreakerRatingConstraint("C-ROOT:device", 6.0, "Existing breaker"),),
        )[0]
        self.assertEqual(assessment.status, "RATING_EXCEEDED")
        self.assertLess(assessment.margin_a, 0)
        self.assertIn("protection compliance", assessment.limitation)

    def test_empty_board_incomer_constraint_reports_no_demand(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Empty board")
        hierarchy = calculate_board_hierarchy(graph)
        assessment = assess_breaker_constraints(
            graph,
            hierarchy,
            (BreakerRatingConstraint("incomer", 16.0, "Existing incomer"),),
        )[0]
        self.assertEqual(assessment.status, "NO_DEMAND")
        self.assertEqual(assessment.required_current_a, 0.0)

    def test_constraints_require_catalog_rating_and_provenance(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        with self.assertRaisesRegex(ValueError, "catalog ratings"):
            assess_breaker_constraints(
                graph,
                hierarchy,
                (BreakerRatingConstraint("incomer", 17.0, "Existing breaker"),),
            )
        with self.assertRaisesRegex(ValueError, "basis_note"):
            assess_breaker_constraints(
                graph,
                hierarchy,
                (BreakerRatingConstraint("incomer", 16.0, ""),),
            )

    def test_duplicate_unknown_and_non_protective_constraints_are_rejected(self):
        graph = self._graph()
        hierarchy = calculate_board_hierarchy(graph)
        with self.assertRaisesRegex(ValueError, "duplicate breaker constraint"):
            assess_breaker_constraints(
                graph,
                hierarchy,
                (
                    BreakerRatingConstraint("incomer", 63.0, "A"),
                    BreakerRatingConstraint("incomer", 63.0, "B"),
                ),
            )
        with self.assertRaisesRegex(ValueError, "unknown node"):
            assess_breaker_constraints(
                graph,
                hierarchy,
                (BreakerRatingConstraint("missing", 16.0, "Known breaker"),),
            )
        with self.assertRaisesRegex(ValueError, "incomer or protective_device"):
            assess_breaker_constraints(
                graph,
                hierarchy,
                (BreakerRatingConstraint("busbar", 16.0, "Not a breaker"),),
            )


if __name__ == "__main__":
    unittest.main()
