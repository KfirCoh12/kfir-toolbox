import tempfile
import unittest
from pathlib import Path

from src.board_persistence import load_last_board, save_last_board
from src.planner_bridge import (
    apply_proposal,
    create_proposal,
    get_project,
    record_fact,
)


class PlannerBridgeTests(unittest.TestCase):
    def _seed(self, path: Path):
        save_last_board(
            {
                "board_id": "DB-01",
                "description": "Shared board",
                "line_to_line_voltage_v": 400.0,
                "line_to_neutral_voltage_v": 230.0,
                "branches": [],
                "uid_counter": 100,
                "selected_node": "busbar",
                "fault_source": {
                    "kind": "TRANSFORMER_TERMINAL",
                    "transformer_rated_power_kva": 1000.0,
                },
            },
            path,
        )

    def test_bridge_records_fact_without_overwriting_shared_fault_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)

            snapshot = record_fact(
                key="occupancy.people",
                value=150,
                provenance="USER_PROVIDED",
                path=path,
            )

            self.assertEqual(snapshot["revision"], 1)
            self.assertEqual(snapshot["facts"]["occupancy.people"]["value"], 150)
            persisted = load_last_board(path)
            self.assertEqual(
                persisted["fault_source"]["transformer_rated_power_kva"],
                1000.0,
            )

    def test_bridge_proposal_is_previewed_before_apply_and_then_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)

            proposed = create_proposal(
                title="Initial circuit",
                reason="Known load",
                operations=[
                    {
                        "kind": "ADD_BRANCH",
                        "branch_kind": "circuit",
                        "parent_uid": "root",
                        "values": {
                            "circuit_id": "C-01",
                            "description": "Office load",
                            "load_kw": 8.0,
                            "phase": "three",
                        },
                    }
                ],
                path=path,
            )
            proposal_id = proposed["created_proposal_id"]

            # Proposal creation changes project metadata, not the live board.
            persisted = load_last_board(path)
            self.assertEqual(persisted["branches"], [])

            applied = apply_proposal(proposal_id=proposal_id, path=path)
            self.assertEqual(applied["revision"], 1)
            self.assertEqual(applied["board"]["branches"][0]["circuit_id"], "C-01")
            self.assertTrue(applied["review"]["calculated"])

            persisted = load_last_board(path)
            self.assertEqual(persisted["branches"][0]["circuit_id"], "C-01")
            self.assertEqual(
                persisted["fault_source"]["transformer_rated_power_kva"],
                1000.0,
            )

    def test_get_project_exposes_compact_ai_ready_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)
            snapshot = get_project(path=path)

            self.assertEqual(snapshot["revision"], 0)
            self.assertEqual(snapshot["board"]["board_id"], "DB-01")
            self.assertIn("facts", snapshot)
            self.assertIn("open_questions", snapshot)
            self.assertIn("pending_proposals", snapshot)
            self.assertIn("review", snapshot)
            self.assertEqual(
                snapshot["engineering_context"]["fault_source"]["kind"],
                "TRANSFORMER_TERMINAL",
            )


if __name__ == "__main__":
    unittest.main()
