import tempfile
import unittest
from pathlib import Path

from src.board_persistence import load_last_board, save_last_board
from src.planner_tool_contract import (
    execute_planner_tool,
    planner_tool_definitions,
)


class PlannerToolContractTests(unittest.TestCase):
    def _seed(self, path: Path):
        save_last_board(
            {
                "board_id": "DB-01",
                "description": "Tool contract board",
                "line_to_line_voltage_v": 400.0,
                "line_to_neutral_voltage_v": 230.0,
                "branches": [],
                "uid_counter": 100,
                "selected_node": "busbar",
            },
            path,
        )

    def test_tool_contract_exposes_only_safe_bridge_actions(self):
        names = tuple(item["name"] for item in planner_tool_definitions())
        self.assertEqual(
            names,
            (
                "get_project",
                "record_fact",
                "add_question",
                "resolve_question",
                "create_board_proposal",
                "preview_board_proposal",
                "apply_board_proposal",
                "reject_board_proposal",
            ),
        )
        self.assertNotIn("write_json", names)
        self.assertNotIn("set_cable_size", names)

    def test_end_to_end_pre_api_flow(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)

            execute_planner_tool(
                "record_fact",
                {
                    "key": "occupancy.people",
                    "value": 150,
                    "provenance": "USER_PROVIDED",
                },
                path=path,
            )
            question = execute_planner_tool(
                "add_question",
                {
                    "prompt": "Provide HVAC electrical load schedule.",
                    "priority": "NEEDED_SOON",
                    "related_keys": ["loads.hvac"],
                },
                path=path,
            )
            self.assertEqual(question["created_question_id"], "Q-001")

            proposed = execute_planner_tool(
                "create_board_proposal",
                {
                    "title": "General power field",
                    "reason": "Create an initial office distribution concept.",
                    "operations": [
                        {
                            "kind": "ADD_BRANCH",
                            "ref": "gp",
                            "branch_kind": "field",
                            "parent_uid": "root",
                            "values": {
                                "feeder_id": "F-GP",
                                "field_id": "GP",
                                "description": "General power",
                            },
                        },
                        {
                            "kind": "ADD_BRANCH",
                            "branch_kind": "circuit",
                            "parent_uid": "@gp",
                            "values": {
                                "circuit_id": "GP-01",
                                "description": "Workstation sockets",
                                "phase": "single",
                                "load_kw": 3.0,
                            },
                        },
                    ],
                    "assumptions": [
                        "Workstation grouping is provisional until the floor plan is reviewed."
                    ],
                },
                path=path,
            )
            proposal_id = proposed["created_proposal_id"]

            # The future model may propose, but the working board remains unchanged
            # until the engineer approves it.
            self.assertEqual(load_last_board(path)["branches"], [])

            preview = execute_planner_tool(
                "preview_board_proposal",
                {"proposal_id": proposal_id},
                path=path,
            )
            self.assertEqual(len(preview["board"]["branches"]), 2)
            self.assertTrue(preview["review"]["calculated"])

            applied = execute_planner_tool(
                "apply_board_proposal",
                {"proposal_id": proposal_id},
                path=path,
            )
            self.assertEqual(len(applied["board"]["branches"]), 2)
            self.assertEqual(applied["revision"], 2)
            self.assertEqual(load_last_board(path)["branches"][1]["circuit_id"], "GP-01")

    def test_unknown_tool_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown Planner tool"):
            execute_planner_tool("direct_database_write", {})


if __name__ == "__main__":
    unittest.main()
