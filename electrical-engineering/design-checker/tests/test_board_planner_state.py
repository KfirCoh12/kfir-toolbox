import unittest

from src.board_planner_state import (
    add_planner_branch,
    planner_owned_payload,
    remove_planner_branch_tree,
)


class BoardPlannerStateTests(unittest.TestCase):
    def test_planner_payload_does_not_copy_other_page_metadata(self):
        board = {
            "board_id": "DB-01",
            "description": "Board",
            "line_to_line_voltage_v": 400.0,
            "line_to_neutral_voltage_v": 230.0,
            "branches": [],
            "uid_counter": 100,
            "fault_source": {"basis": "transformer"},
            "feeder_lengths_m": {"F-01": 30.0},
        }
        payload = planner_owned_payload(board)
        self.assertEqual(payload["board_id"], "DB-01")
        self.assertNotIn("fault_source", payload)
        self.assertNotIn("feeder_lengths_m", payload)

    def test_add_and_remove_branch_tree(self):
        board = {"branches": [], "uid_counter": 100}
        field_uid = add_planner_branch(board, "field")
        circuit_uid = add_planner_branch(board, "circuit", field_uid)
        sub_uid = add_planner_branch(board, "sub_board", field_uid)
        add_planner_branch(board, "circuit", sub_uid)

        self.assertEqual(len(board["branches"]), 4)
        self.assertEqual(board["uid_counter"], 104)
        self.assertNotEqual(field_uid, circuit_uid)

        removed = set(remove_planner_branch_tree(board, field_uid))
        self.assertEqual(removed, {field_uid, circuit_uid, sub_uid, "b104"})
        self.assertEqual(board["branches"], [])

    def test_generated_ids_do_not_collide_with_existing_ids(self):
        board = {
            "uid_counter": 200,
            "branches": [
                {
                    "uid": "b1",
                    "kind": "final",
                    "parent_key": "root",
                    "circuit_id": "C-01",
                },
                {
                    "uid": "b2",
                    "kind": "field",
                    "parent_key": "root",
                    "feeder_id": "F-01",
                    "field_id": "FIELD-01",
                },
            ],
        }
        circuit_uid = add_planner_branch(board, "circuit")
        field_uid = add_planner_branch(board, "field")
        by_uid = {item["uid"]: item for item in board["branches"]}
        self.assertEqual(by_uid[circuit_uid]["circuit_id"], "C-02")
        self.assertEqual(by_uid[field_uid]["feeder_id"], "F-02")
        self.assertEqual(by_uid[field_uid]["field_id"], "FIELD-02")


if __name__ == "__main__":
    unittest.main()
