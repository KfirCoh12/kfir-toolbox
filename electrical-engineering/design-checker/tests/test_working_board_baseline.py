import tempfile
import unittest
from pathlib import Path

from src.board_persistence import load_last_board, save_last_board
from src.working_board_baseline import (
    ensure_office_working_baseline,
    is_legacy_small_protection_test_board,
)


class WorkingBoardBaselineTests(unittest.TestCase):
    def legacy_board(self):
        return {
            "board_id": "MAIN-LV",
            "description": "Protection test board",
            "line_to_line_voltage_v": 400.0,
            "line_to_neutral_voltage_v": 230.0,
            "uid_counter": 102,
            "branches": [
                {
                    "uid": "b101",
                    "kind": "field",
                    "parent_key": "root",
                    "feeder_id": "F-01",
                    "field_id": "FIELD-01",
                    "description": "New field",
                    "material": "copper",
                },
                {
                    "uid": "b102",
                    "kind": "final",
                    "parent_key": "b101",
                    "circuit_id": "C-01",
                    "description": "New load",
                    "mode": "auto",
                    "load_kw": 45.0,
                    "phase": "three",
                    "power_factor": 0.9,
                    "demand_factor": 1.0,
                    "material": "copper",
                    "phase_preference": "Auto",
                    "connection_option_id": None,
                },
            ],
        }

    def test_detector_matches_only_known_legacy_demo_shape(self):
        board = self.legacy_board()
        self.assertTrue(is_legacy_small_protection_test_board(board))
        board["description"] = "My project"
        self.assertFalse(is_legacy_small_protection_test_board(board))

    def test_missing_board_is_seeded_with_office_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.json"
            board, changed = ensure_office_working_baseline(path)
            self.assertTrue(changed)
            self.assertEqual(board["declared_main_incomer_a"], 400.0)
            self.assertEqual(len([b for b in board["branches"] if b["kind"] == "final"]), 40)
            self.assertEqual(load_last_board(path)["board_id"], board["board_id"])

    def test_known_legacy_demo_is_replaced_but_custom_board_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.json"
            save_last_board(self.legacy_board(), path)
            board, changed = ensure_office_working_baseline(path)
            self.assertTrue(changed)
            self.assertEqual(board["declared_main_incomer_a"], 400.0)

            custom = dict(board)
            custom["board_id"] = "CUSTOM-DB"
            save_last_board(custom, path)
            preserved, changed = ensure_office_working_baseline(path)
            self.assertFalse(changed)
            self.assertEqual(preserved["board_id"], "CUSTOM-DB")


if __name__ == "__main__":
    unittest.main()
