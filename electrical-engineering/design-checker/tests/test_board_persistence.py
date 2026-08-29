import json
import tempfile
import unittest
from pathlib import Path

from src.board_persistence import clear_last_board, load_last_board, save_last_board


class BoardPersistenceTests(unittest.TestCase):
    def test_round_trip_preserves_board_working_state(self):
        payload = {
            "board_id": "DB-01",
            "description": "Office board",
            "line_to_line_voltage_v": 400.0,
            "line_to_neutral_voltage_v": 230.0,
            "uid_counter": 104,
            "selected_node": "branch:b104",
            "branches": [
                {
                    "uid": "b104",
                    "kind": "final",
                    "parent_key": "root",
                    "circuit_id": "C-01",
                    "description": "Lighting",
                    "mode": "auto",
                    "load_kw": 2.5,
                    "phase": "single",
                    "power_factor": 0.9,
                    "demand_factor": 1.0,
                    "material": "copper",
                    "phase_preference": "L1",
                    "connection_option_id": None,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board(payload, path)
            self.assertEqual(load_last_board(path), payload)

    def test_save_uses_versioned_json_envelope(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({"branches": []}, path)
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["schema_version"], 1)
            self.assertEqual(document["board"], {"branches": []})

    def test_legacy_widget_minimum_supply_is_repaired_on_load(self):
        payload = {
            "board_id": "DB-01",
            "description": "Board",
            "line_to_line_voltage_v": 1.0,
            "line_to_neutral_voltage_v": 1.0,
            "branches": [],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            document = {"schema_version": 1, "board": payload}
            path.write_text(json.dumps(document), encoding="utf-8")
            loaded = load_last_board(path)
            self.assertEqual(loaded["line_to_line_voltage_v"], 400.0)
            self.assertEqual(loaded["line_to_neutral_voltage_v"], 230.0)

    def test_widget_minimum_reset_does_not_overwrite_existing_valid_supply(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({
                "board_id": "DB-01",
                "description": "Board",
                "line_to_line_voltage_v": 415.0,
                "line_to_neutral_voltage_v": 240.0,
                "branches": [],
            }, path)
            save_last_board({
                "board_id": "DB-01",
                "description": "Board",
                "line_to_line_voltage_v": 1.0,
                "line_to_neutral_voltage_v": 1.0,
                "branches": [],
            }, path)
            loaded = load_last_board(path)
            self.assertEqual(loaded["line_to_line_voltage_v"], 415.0)
            self.assertEqual(loaded["line_to_neutral_voltage_v"], 240.0)

    def test_other_supply_values_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({
                "board_id": "DB-01",
                "description": "Board",
                "line_to_line_voltage_v": 480.0,
                "line_to_neutral_voltage_v": 277.0,
                "branches": [],
            }, path)
            loaded = load_last_board(path)
            self.assertEqual(loaded["line_to_line_voltage_v"], 480.0)
            self.assertEqual(loaded["line_to_neutral_voltage_v"], 277.0)

    def test_clear_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({"branches": []}, path)
            clear_last_board(path)
            clear_last_board(path)
            self.assertFalse(path.exists())

    def test_invalid_json_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Could not read saved Board Planner state"):
                load_last_board(path)


if __name__ == "__main__":
    unittest.main()
