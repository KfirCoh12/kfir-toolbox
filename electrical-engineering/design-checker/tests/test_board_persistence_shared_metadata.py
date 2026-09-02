import tempfile
import unittest
from pathlib import Path

from src.board_persistence import load_last_board, save_last_board


class SharedBoardMetadataPersistenceTests(unittest.TestCase):
    def test_partial_planner_autosave_preserves_fault_and_path_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({
                "board_id": "MAIN-LV",
                "description": "Protection test board",
                "branches": [{"uid": "b1", "kind": "field"}],
                "fault_source": {
                    "kind": "TRANSFORMER_TERMINAL",
                    "transformer_rated_power_kva": 1000.0,
                    "transformer_impedance_percent": 6.0,
                    "evidence_record_ref": "TEST-TX-01",
                    "rule_basis_ref": "TEST-FAULT-BASIS-01",
                },
                "fault_path_lengths_m": {"F-01": 30.0},
            }, path)

            # Mirrors Board Planner: it owns the structural fields and does not know
            # about Protection Checks' project metadata.
            save_last_board({
                "board_id": "MAIN-LV",
                "description": "Protection test board edited",
                "line_to_line_voltage_v": 400.0,
                "line_to_neutral_voltage_v": 230.0,
                "uid_counter": 101,
                "selected_node": "busbar",
                "branches": [{"uid": "b1", "kind": "field"}],
            }, path)

            loaded = load_last_board(path)
            self.assertEqual(loaded["description"], "Protection test board edited")
            self.assertEqual(loaded["fault_source"]["transformer_rated_power_kva"], 1000.0)
            self.assertEqual(loaded["fault_source"]["transformer_impedance_percent"], 6.0)
            self.assertEqual(loaded["fault_path_lengths_m"], {"F-01": 30.0})

    def test_explicit_shared_metadata_update_replaces_existing_value(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({
                "board_id": "MAIN-LV",
                "branches": [],
                "fault_source": {"kind": "TRANSFORMER_TERMINAL"},
            }, path)
            save_last_board({"fault_source": {"kind": "NONE"}}, path)

            loaded = load_last_board(path)
            self.assertEqual(loaded["board_id"], "MAIN-LV")
            self.assertEqual(loaded["fault_source"], {"kind": "NONE"})

    def test_explicit_none_is_not_treated_as_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            save_last_board({
                "board_id": "MAIN-LV",
                "project_note": "keep until explicitly cleared",
            }, path)
            save_last_board({"project_note": None}, path)

            self.assertIsNone(load_last_board(path)["project_note"])


if __name__ == "__main__":
    unittest.main()
