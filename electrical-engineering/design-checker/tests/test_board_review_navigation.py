import unittest

from src.board_review_navigation import branch_uid_for_route_id


class BoardReviewNavigationTests(unittest.TestCase):
    def setUp(self):
        self.board = {
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
                {
                    "uid": "b3",
                    "kind": "sub_board",
                    "parent_key": "root",
                    "feeder_id": "SB-01",
                    "sub_board_id": "DB-02",
                },
            ]
        }

    def test_final_circuit_route_maps_to_final_branch(self):
        self.assertEqual(branch_uid_for_route_id(self.board, "C-01"), "b1")

    def test_field_and_sub_board_feeder_routes_map_to_owning_branches(self):
        self.assertEqual(branch_uid_for_route_id(self.board, "F-01"), "b2")
        self.assertEqual(branch_uid_for_route_id(self.board, "SB-01"), "b3")

    def test_unknown_or_blank_route_has_no_branch_selection(self):
        self.assertIsNone(branch_uid_for_route_id(self.board, "UNKNOWN"))
        self.assertIsNone(branch_uid_for_route_id(self.board, None))
        self.assertIsNone(branch_uid_for_route_id(self.board, "  "))

    def test_duplicate_route_ownership_is_rejected(self):
        self.board["branches"].append(
            {
                "uid": "b4",
                "kind": "field",
                "parent_key": "root",
                "feeder_id": "F-01",
                "field_id": "FIELD-02",
            }
        )
        with self.assertRaisesRegex(ValueError, "multiple planner branches"):
            branch_uid_for_route_id(self.board, "F-01")

    def test_malformed_branch_collection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "branches must be a list"):
            branch_uid_for_route_id({"branches": {}}, "C-01")


if __name__ == "__main__":
    unittest.main()
