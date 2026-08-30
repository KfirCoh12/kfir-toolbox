import unittest
from dataclasses import replace

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_planner import calculate_board_hierarchy
from src.protection_planning import (
    feeder_protection_plan,
    hierarchy_protection_plans,
)


class ProtectionPlanningIntegrationTests(unittest.TestCase):
    def _calculated_hierarchy(self):
        graph = make_radial_board_graph(board_id="MDB", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-01",
            sub_board_id="DB-01",
            description="Sub-board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Child three-phase load",
            load_kw=18.0,
            phase="three",
            parent_busbar_id="F-01:DB-01:busbar",
        )
        return calculate_board_hierarchy(graph)

    def test_hierarchy_exposes_separate_incomer_and_feeder_planning_records(self):
        records = hierarchy_protection_plans(self._calculated_hierarchy())

        self.assertEqual(len(records), 3)
        self.assertEqual(
            {(record.kind, record.device_ref) for record in records},
            {
                ("BOARD_INCOMER", "MDB:incomer"),
                ("BOARD_INCOMER", "DB-01:incomer"),
                ("SUB_BOARD_FEEDER", "F-01:device"),
            },
        )
        for record in records:
            self.assertGreater(record.design_current_a, 0)
            self.assertEqual(record.plan.candidate.status, "CANDIDATE")
            self.assertIsNotNone(record.breaker_candidate_a)
            self.assertEqual(record.plan.coordination.protection_status, "NOT CHECKED")
            self.assertEqual(record.plan.coordination.selectivity_status, "NOT CHECKED")

    def test_requesting_checks_does_not_promote_rating_hierarchy_to_verified(self):
        records = hierarchy_protection_plans(
            self._calculated_hierarchy(),
            protection_check_requested=True,
            selectivity_check_requested=True,
        )

        for record in records:
            self.assertEqual(record.plan.coordination.protection_status, "INSUFFICIENT DATA")
            self.assertEqual(record.plan.coordination.selectivity_status, "INSUFFICIENT DATA")
            self.assertNotEqual(record.plan.coordination.protection_status, "VERIFIED")
            self.assertNotEqual(record.plan.coordination.selectivity_status, "VERIFIED")
            self.assertIn(
                "manufacturer selectivity/coordination table or verified time-current evidence",
                record.plan.coordination.missing_evidence,
            )

    def test_no_demand_feeder_does_not_synthesize_zero_current_breaker_plan(self):
        graph = make_radial_board_graph(board_id="MDB", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-EMPTY",
            sub_board_id="DB-EMPTY",
            description="Empty board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="ROOT-C01",
            description="Root load",
            load_kw=9.0,
            phase="three",
        )
        result = calculate_board_hierarchy(graph)

        self.assertEqual(result.feeder_rollups[0].status, "NO_DEMAND")
        records = hierarchy_protection_plans(result)
        self.assertEqual(
            {(record.kind, record.device_ref) for record in records},
            {("BOARD_INCOMER", "MDB:incomer")},
        )

    def test_existing_feeder_candidate_must_match_shared_protection_candidate(self):
        rollup = self._calculated_hierarchy().feeder_rollups[0]
        inconsistent = replace(
            rollup,
            breaker_candidate_a=float(rollup.breaker_candidate_a) + 1.0,
        )

        with self.assertRaisesRegex(ValueError, "disagrees with protection planner"):
            feeder_protection_plan(inconsistent)

    def test_feeder_plan_keeps_load_sizing_separate_from_selectivity(self):
        rollup = self._calculated_hierarchy().feeder_rollups[0]
        plan = feeder_protection_plan(rollup, selectivity_check_requested=True)

        self.assertEqual(plan.candidate.breaker_rating_a, rollup.breaker_candidate_a)
        self.assertEqual(plan.candidate.status, "CANDIDATE")
        self.assertEqual(plan.coordination.protection_status, "NOT CHECKED")
        self.assertEqual(plan.coordination.selectivity_status, "INSUFFICIENT DATA")


if __name__ == "__main__":
    unittest.main()
