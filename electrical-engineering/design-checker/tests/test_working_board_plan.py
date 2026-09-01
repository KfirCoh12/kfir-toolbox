import unittest

from src.protection_hierarchy import protection_relationships
from src.working_board_plan import calculate_working_board


class WorkingBoardPlanTests(unittest.TestCase):
    def _field_payload(self):
        return {
            "board_id": "MAIN-LV",
            "description": "Protection test board",
            "line_to_line_voltage_v": 400.0,
            "line_to_neutral_voltage_v": 230.0,
            "branches": [
                {
                    "uid": "b1",
                    "kind": "field",
                    "parent_key": "root",
                    "feeder_id": "F-01",
                    "field_id": "FIELD-01",
                    "description": "Test field",
                    "material": "copper",
                },
                {
                    "uid": "b2",
                    "kind": "final",
                    "parent_key": "b1",
                    "circuit_id": "C-01",
                    "description": "Test load",
                    "mode": "auto",
                    "load_kw": 45.0,
                    "phase": "three",
                    "power_factor": 0.90,
                    "demand_factor": 1.0,
                    "material": "copper",
                    "phase_preference": "Auto",
                },
            ],
        }

    def test_reuses_board_planner_results_for_protection_context(self):
        calculated = calculate_working_board(self._field_payload())
        contexts = calculated.context_by_circuit_id

        self.assertIn("C-01", contexts)
        self.assertIn("F-01", contexts)
        self.assertGreater(contexts["C-01"].design_current_a, 0)
        self.assertEqual(contexts["C-01"].breaker_candidate_a, 80.0)
        self.assertEqual(contexts["C-01"].cable_mm2, 25.0)
        self.assertGreater(contexts["F-01"].design_current_a, 0)
        self.assertEqual(contexts["F-01"].breaker_candidate_a, 80.0)
        self.assertEqual(contexts["F-01"].cable_mm2, 25.0)

    def test_enriched_graph_carries_incomer_and_branch_ratings(self):
        calculated = calculate_working_board(self._field_payload())
        graph = calculated.graph

        self.assertEqual(graph.node_by_id["incomer"].rating_a, 80.0)
        self.assertEqual(graph.node_by_id["F-01:device"].rating_a, 80.0)
        self.assertEqual(graph.node_by_id["C-01:device"].rating_a, 80.0)

        relationships = protection_relationships(graph)
        by_circuit = {item.downstream_circuit_id: item for item in relationships}
        self.assertEqual(by_circuit["F-01"].upstream_rating_a, 80.0)
        self.assertEqual(by_circuit["F-01"].downstream_rating_a, 80.0)
        self.assertEqual(by_circuit["C-01"].upstream_rating_a, 80.0)
        self.assertEqual(by_circuit["C-01"].downstream_rating_a, 80.0)

    def test_manual_branch_preserves_fixed_current_basis(self):
        payload = self._field_payload()
        branch = payload["branches"][1]
        branch.update({
            "mode": "manual",
            "connection_option_id": "industrial_63a_3ph",
        })
        calculated = calculate_working_board(payload)
        context = calculated.context_by_circuit_id["C-01"]
        self.assertEqual(context.design_current_a, 63.0)
        self.assertEqual(context.breaker_candidate_a, 63.0)


if __name__ == "__main__":
    unittest.main()
