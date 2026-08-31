import unittest

from src.protection_hierarchy import protection_relationships
from src.working_board_graph import graph_from_working_board


class WorkingBoardGraphTests(unittest.TestCase):
    def _payload(self):
        return {
            "board_id": "DB-01",
            "description": "Main board",
            "line_to_line_voltage_v": 400.0,
            "line_to_neutral_voltage_v": 230.0,
            "branches": [
                {
                    "uid": "b1",
                    "kind": "final",
                    "parent_key": "root",
                    "circuit_id": "C-01",
                    "description": "Socket circuit",
                    "mode": "auto",
                    "load_kw": 8.0,
                    "phase": "three",
                    "power_factor": 0.9,
                    "demand_factor": 1.0,
                    "material": "copper",
                    "phase_preference": "Auto",
                },
                {
                    "uid": "b2",
                    "kind": "sub_board",
                    "parent_key": "root",
                    "feeder_id": "F-01",
                    "sub_board_id": "DB-02",
                    "description": "Sub board",
                },
                {
                    "uid": "b3",
                    "kind": "final",
                    "parent_key": "b2",
                    "circuit_id": "C-02",
                    "description": "Downstream load",
                    "mode": "auto",
                    "load_kw": 5.0,
                    "phase": "single",
                    "power_factor": 0.95,
                    "demand_factor": 0.8,
                    "material": "copper",
                    "phase_preference": "L1",
                },
            ],
        }

    def test_reconstructs_saved_hierarchy_for_secondary_pages(self):
        graph = graph_from_working_board(self._payload())
        self.assertEqual(graph.board_id, "DB-01")
        self.assertIn("F-01:DB-02:busbar", graph.node_by_id)
        self.assertIn("C-02:load", graph.node_by_id)

        relationships = protection_relationships(graph)
        self.assertGreaterEqual(len(relationships), 2)
        self.assertTrue(any(item.downstream_circuit_id == "C-01" for item in relationships))
        self.assertTrue(any(item.downstream_circuit_id == "F-01" for item in relationships))

    def test_rejects_branch_with_missing_parent(self):
        payload = self._payload()
        payload["branches"][0]["parent_key"] = "missing"
        with self.assertRaisesRegex(ValueError, "unavailable parent"):
            graph_from_working_board(payload)

    def test_manual_branch_does_not_invent_consumer_load(self):
        payload = self._payload()
        payload["branches"][0]["mode"] = "manual"
        graph = graph_from_working_board(payload)
        load = graph.node_by_id["C-01:load"]
        self.assertIsNone(load.load_kw)


if __name__ == "__main__":
    unittest.main()
