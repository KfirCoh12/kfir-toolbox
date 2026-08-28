import unittest
from dataclasses import replace

from src.board_boundaries import calculation_boundaries_from_graph
from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.board_planner import calculate_board_plan
from src.board_summaries import board_hierarchy_summaries


class BoardHierarchySummaryTests(unittest.TestCase):
    def test_uncalculated_and_empty_boards_remain_explicit(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Child load",
            phase="three",
            parent_busbar_id="F-01:DB-L1:busbar",
        )

        root, child = board_hierarchy_summaries(graph)
        self.assertEqual(root.status, "NO_FINAL_LOADS")
        self.assertEqual(root.feeder_demand_status, "ROOT_BOARD")
        self.assertEqual(child.status, "UNCALCULATED")
        self.assertEqual(child.final_load_count, 1)
        self.assertEqual(child.feeder_circuit_id, "F-01")
        self.assertEqual(child.feeder_demand_status, "NOT_EVALUATED")
        self.assertIsNone(child.l1_current_a)
        self.assertIsNone(child.local_incomer_candidate_a)

    def test_matching_local_plan_populates_only_local_summary_fields(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Child three phase load",
            phase="three",
            load_kw=18.0,
            parent_busbar_id="F-01:DB-L1:busbar",
        )
        child_boundary = calculation_boundaries_from_graph(graph)[1]
        plan = calculate_board_plan(child_boundary.request)

        root, child = board_hierarchy_summaries(graph, (plan,))
        self.assertEqual(root.status, "NO_FINAL_LOADS")
        self.assertEqual(child.status, "CALCULATED")
        self.assertTrue(child.has_local_calculation)
        self.assertEqual(child.local_scope_status, plan.scope_status)
        self.assertAlmostEqual(child.l1_current_a, plan.phase_balance.l1_current_a)
        self.assertAlmostEqual(child.l2_current_a, plan.phase_balance.l2_current_a)
        self.assertAlmostEqual(child.l3_current_a, plan.phase_balance.l3_current_a)
        self.assertAlmostEqual(child.phase_spread_a, plan.phase_balance.spread_a)
        self.assertEqual(
            child.local_incomer_candidate_a,
            plan.incomer_candidate.breaker_rating_a,
        )
        self.assertEqual(
            child.local_incomer_required_current_a,
            plan.incomer_candidate.required_current_a,
        )
        # A local board result must not be silently reinterpreted as feeder demand.
        self.assertEqual(child.feeder_demand_status, "NOT_EVALUATED")

    def test_multiple_nested_local_plans_stay_attached_to_their_own_boards(self):
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
            load_kw=12.0,
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
            load_kw=30.0,
            parent_busbar_id="F-02:DB-L2:busbar",
        )
        boundaries = calculation_boundaries_from_graph(graph)
        plans = tuple(
            calculate_board_plan(boundary.request)
            for boundary in boundaries
            if boundary.request is not None
        )
        summaries = board_hierarchy_summaries(graph, plans)
        by_id = {summary.board_id: summary for summary in summaries}

        self.assertEqual(by_id["MDB"].status, "NO_FINAL_LOADS")
        self.assertEqual(by_id["DB-L1"].status, "CALCULATED")
        self.assertEqual(by_id["DB-L2"].status, "CALCULATED")
        self.assertNotEqual(
            by_id["DB-L1"].local_incomer_required_current_a,
            by_id["DB-L2"].local_incomer_required_current_a,
        )
        self.assertEqual(by_id["DB-L1"].feeder_demand_status, "NOT_EVALUATED")
        self.assertEqual(by_id["DB-L2"].feeder_demand_status, "NOT_EVALUATED")

    def test_wrong_or_duplicate_plans_are_rejected(self):
        graph = add_radial_circuit(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            circuit_id="C-01",
            description="Root load",
            phase="three",
        )
        boundary = calculation_boundaries_from_graph(graph)[0]
        plan = calculate_board_plan(boundary.request)

        with self.assertRaisesRegex(ValueError, "duplicate board plan"):
            board_hierarchy_summaries(graph, (plan, plan))

        wrong = replace(plan, request=replace(plan.request, board_id="OTHER"))
        with self.assertRaisesRegex(ValueError, "does not belong to this hierarchy"):
            board_hierarchy_summaries(graph, (wrong,))

        wrong_circuit = replace(
            plan,
            request=replace(
                plan.request,
                circuits=(replace(plan.request.circuits[0], circuit_id="OTHER-C"),),
            ),
        )
        with self.assertRaisesRegex(ValueError, "circuits do not match hierarchy boundary"):
            board_hierarchy_summaries(graph, (wrong_circuit,))


if __name__ == "__main__":
    unittest.main()
