import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_planner import calculate_board_hierarchy


class HierarchyPlannerTests(unittest.TestCase):
    def test_child_board_phase_vector_rolls_into_parent_without_flattening(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Lighting sub-board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-ROOT",
            description="Root load",
            load_kw=4.0,
            phase="three",
            parent_busbar_id="busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-CHILD-1",
            description="Child L1",
            load_kw=2.3,
            phase="single",
            phase_preference="L1",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-CHILD-2",
            description="Child L2",
            load_kw=1.15,
            phase="single",
            phase_preference="L2",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

        result = calculate_board_hierarchy(graph)
        plans = result.plans_by_board_id
        self.assertEqual(set(plans), {"DB-01", "DB-02"})
        self.assertEqual(tuple(c.request.circuit_id for c in plans["DB-02"].circuits), ("C-CHILD-1", "C-CHILD-2"))
        self.assertEqual(tuple(c.request.circuit_id for c in plans["DB-01"].circuits), ("C-ROOT",))

        child = plans["DB-02"].phase_balance
        contribution = plans["DB-01"].request.phase_contributions[0]
        self.assertAlmostEqual(contribution.l1_current_a, child.l1_current_a)
        self.assertAlmostEqual(contribution.l2_current_a, child.l2_current_a)
        self.assertAlmostEqual(contribution.l3_current_a, child.l3_current_a)
        self.assertEqual(contribution.contribution_id, "DBF-01")

    def test_parent_with_only_sub_board_demand_is_calculated(self):
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
            load_kw=10.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

        result = calculate_board_hierarchy(graph)
        root = result.root
        self.assertEqual(root.status, "CALCULATED")
        self.assertEqual(root.plan.circuit_count, 0)
        self.assertEqual(len(root.plan.request.phase_contributions), 1)
        self.assertGreater(root.plan.incomer_candidate.required_current_a, 0)

    def test_nested_sub_boards_roll_up_recursively(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Middle board",
        )
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-02",
            sub_board_id="DB-03",
            description="Leaf board",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-LEAF",
            description="Leaf load",
            load_kw=9.0,
            phase="three",
            parent_busbar_id="DBF-02:DB-03:busbar",
        )

        result = calculate_board_hierarchy(graph)
        plans = result.plans_by_board_id
        self.assertEqual(set(plans), {"DB-01", "DB-02", "DB-03"})
        self.assertEqual(plans["DB-02"].circuit_count, 0)
        self.assertEqual(plans["DB-01"].circuit_count, 0)
        self.assertEqual(plans["DB-02"].request.phase_contributions[0].contribution_id, "DBF-02")
        self.assertEqual(plans["DB-01"].request.phase_contributions[0].contribution_id, "DBF-01")
        self.assertAlmostEqual(
            plans["DB-01"].phase_balance.max_phase_current_a,
            plans["DB-03"].phase_balance.max_phase_current_a,
        )

    def test_feeder_rollup_exposes_breaker_candidate_but_not_cable(self):
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
            load_kw=18.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

        result = calculate_board_hierarchy(graph)
        rollup = result.feeder_rollups[0]
        self.assertEqual(rollup.board_id, "DB-02")
        self.assertEqual(rollup.parent_board_id, "DB-01")
        self.assertEqual(rollup.feeder_circuit_id, "DBF-01")
        self.assertEqual(rollup.status, "PROVISIONAL")
        self.assertIsNotNone(rollup.breaker_candidate_a)
        self.assertIn("Feeder cable is not sized", rollup.limitations[1])

    def test_empty_downstream_board_does_not_create_fake_parent_demand(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Empty board",
        )
        result = calculate_board_hierarchy(graph)
        self.assertEqual(result.root.status, "NO_DEMAND")
        child = next(board for board in result.boards if board.board_id == "DB-02")
        self.assertEqual(child.status, "NO_DEMAND")
        self.assertEqual(result.feeder_rollups[0].status, "NO_DEMAND")


if __name__ == "__main__":
    unittest.main()
