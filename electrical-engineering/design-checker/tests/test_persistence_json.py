import tempfile
import unittest
from pathlib import Path

from src.board_persistence import load_last_board, save_last_board
from src.persistence_json import dumps_strict, loads_strict


class StrictPersistenceJsonTests(unittest.TestCase):
    def test_encoder_rejects_non_finite_numbers(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Out of range float values"):
                    dumps_strict({"value": value})

    def test_decoder_rejects_non_standard_non_finite_tokens(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ValueError, "Non-finite numeric token"):
                    loads_strict(f'{{"value": {token}}}')

    def test_board_save_rejects_non_finite_engineering_state_without_overwriting_existing_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            valid = {
                "board_id": "DB-01",
                "line_to_line_voltage_v": 400.0,
                "line_to_neutral_voltage_v": 230.0,
                "branches": [],
            }
            save_last_board(valid, path)

            invalid = dict(valid)
            invalid["line_to_line_voltage_v"] = float("nan")
            with self.assertRaises(ValueError):
                save_last_board(invalid, path)

            self.assertEqual(load_last_board(path), valid)

    def test_board_load_rejects_non_standard_non_finite_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            path.write_text(
                '{"schema_version": 1, "board": {"line_to_line_voltage_v": NaN, "branches": []}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Could not read saved Board Planner state"):
                load_last_board(path)


if __name__ == "__main__":
    unittest.main()
