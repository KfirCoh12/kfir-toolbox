import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.board_persistence import (
    board_autosave_path,
    clear_last_board,
    load_last_board,
    persistence_scope_for_email,
    save_last_board,
    storage_key_for_email,
    toolbox_data_root,
)


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

    def test_hosted_data_directory_can_be_configured_without_changing_callers(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"KFIR_TOOLBOX_DATA_DIR": folder}):
                self.assertEqual(toolbox_data_root(), Path(folder))
                self.assertEqual(
                    board_autosave_path(),
                    Path(folder) / "board-planner" / "last_board.json",
                )
                payload = {"board_id": "DB-01", "branches": []}
                save_last_board(payload)
                self.assertEqual(load_last_board(), payload)

    def test_blank_hosted_data_directory_keeps_local_default(self):
        with patch.dict(os.environ, {"KFIR_TOOLBOX_DATA_DIR": "   "}):
            self.assertEqual(toolbox_data_root(), Path.home() / ".kfir-toolbox")

    def test_authenticated_users_get_distinct_opaque_hosted_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"KFIR_TOOLBOX_DATA_DIR": folder}):
                with persistence_scope_for_email("One@Example.com"):
                    first = board_autosave_path()
                with persistence_scope_for_email("two@example.com"):
                    second = board_autosave_path()

        self.assertNotEqual(first, second)
        self.assertEqual(first.parent.parent.parent, Path(folder) / "users")
        self.assertNotIn("one@example.com", str(first).lower())
        self.assertNotIn("two@example.com", str(second).lower())

    def test_authenticated_user_scope_is_deterministic_and_normalized(self):
        self.assertEqual(
            storage_key_for_email(" Owner@Example.com "),
            storage_key_for_email("owner@example.com"),
        )

    def test_authenticated_users_cannot_overwrite_each_others_autosave(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"KFIR_TOOLBOX_DATA_DIR": folder}):
                with persistence_scope_for_email("one@example.com"):
                    save_last_board({"board_id": "DB-ONE", "branches": []})
                with persistence_scope_for_email("two@example.com"):
                    save_last_board({"board_id": "DB-TWO", "branches": []})

                with persistence_scope_for_email("one@example.com"):
                    self.assertEqual(load_last_board()["board_id"], "DB-ONE")
                with persistence_scope_for_email("two@example.com"):
                    self.assertEqual(load_last_board()["board_id"], "DB-TWO")

    def test_user_scope_does_not_leak_after_context_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"KFIR_TOOLBOX_DATA_DIR": folder}):
                with persistence_scope_for_email("owner@example.com"):
                    self.assertIn("users", board_autosave_path().parts)
                self.assertEqual(
                    board_autosave_path(),
                    Path(folder) / "board-planner" / "last_board.json",
                )

    def test_blank_authenticated_email_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Authenticated email is required"):
            storage_key_for_email("   ")

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

    def test_save_flushes_file_and_directory_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            real_fsync = os.fsync
            calls = []

            def recording_fsync(fd):
                calls.append(fd)
                return real_fsync(fd)

            with patch("src.board_persistence.os.fsync", side_effect=recording_fsync):
                save_last_board({"branches": []}, path)

            self.assertGreaterEqual(len(calls), 2)
            self.assertEqual(load_last_board(path), {"branches": []})

    def test_failed_replace_preserves_existing_save_and_cleans_temp_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            original = {"schema_version": 1, "board": {"board_id": "DB-OLD", "branches": []}}
            path.write_text(json.dumps(original), encoding="utf-8")

            with patch("src.board_persistence.Path.replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    save_last_board({"board_id": "DB-NEW", "branches": []}, path)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)
            self.assertEqual(list(Path(folder).glob(".last_board.json.*.tmp")), [])

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
