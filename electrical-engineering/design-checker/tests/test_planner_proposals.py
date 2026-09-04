import unittest

from src.planner_proposals import (
    apply_board_proposal,
    create_board_proposal,
    pending_board_proposals,
    preview_board_proposal,
)
from src.project_state import record_project_fact


def _board():
    return {
        "board_id": "DB-01",
        "description": "Test board",
        "line_to_line_voltage_v": 400.0,
        "line_to_neutral_voltage_v": 230.0,
        "branches": [],
        "uid_counter": 100,
        "selected_node": "busbar",
    }


class PlannerProposalTests(unittest.TestCase):
    def test_proposal_can_build_nested_structure_with_local_refs(self):
        payload, proposal_id = create_board_proposal(
            _board(),
            title="Create office field",
            reason="Initial board concept",
            operations=[
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
            assumptions=("Workstation grouping is provisional.",),
        )

        # Creating the proposal stores intent only; the live board is unchanged.
        self.assertEqual(payload["branches"], [])
        proposal = pending_board_proposals(payload)[0]
        self.assertEqual(proposal["proposal_id"], proposal_id)
        self.assertEqual(proposal["base_revision"], 0)

        preview, calculated, review = preview_board_proposal(payload, proposal_id)
        self.assertEqual(len(preview["branches"]), 2)
        field = preview["branches"][0]
        circuit = preview["branches"][1]
        self.assertEqual(circuit["parent_key"], field["uid"])
        self.assertEqual(circuit["circuit_id"], "GP-01")
        self.assertIsNotNone(calculated)
        self.assertIsNotNone(review)

    def test_apply_advances_revision_and_marks_proposal_applied(self):
        payload, proposal_id = create_board_proposal(
            _board(),
            title="Add circuit",
            reason="Known load",
            operations=[
                {
                    "kind": "ADD_BRANCH",
                    "branch_kind": "circuit",
                    "parent_uid": "root",
                    "values": {
                        "circuit_id": "C-01",
                        "description": "Load",
                        "load_kw": 5.0,
                    },
                }
            ],
        )
        applied = apply_board_proposal(payload, proposal_id)
        self.assertEqual(len(applied["branches"]), 1)
        state = applied["project_state"]
        self.assertEqual(state["revision"], 1)
        self.assertEqual(state["proposals"][0]["status"], "APPLIED")
        self.assertEqual(state["proposals"][0]["applied_revision"], 1)

    def test_stale_proposal_is_rejected_after_project_fact_changes(self):
        payload, proposal_id = create_board_proposal(
            _board(),
            title="Add circuit",
            reason="Initial concept",
            operations=[
                {
                    "kind": "ADD_BRANCH",
                    "branch_kind": "circuit",
                    "parent_uid": "root",
                    "values": {
                        "circuit_id": "C-01",
                        "description": "Load",
                        "load_kw": 5.0,
                    },
                }
            ],
        )
        changed = record_project_fact(
            payload,
            key="supply.rating_a",
            value=400,
            provenance="USER_PROVIDED",
        )
        with self.assertRaisesRegex(ValueError, "stale"):
            apply_board_proposal(changed, proposal_id)

    def test_invalid_hierarchy_never_enters_pending_proposals(self):
        board = _board()
        board["branches"] = [
            {
                "uid": "b101",
                "kind": "final",
                "parent_key": "root",
                "circuit_id": "C-01",
                "description": "Existing load",
                "mode": "auto",
                "load_kw": 5.0,
                "phase": "three",
                "power_factor": 0.9,
                "demand_factor": 1.0,
                "material": "copper",
                "phase_preference": "Auto",
                "connection_option_id": None,
            }
        ]
        board["uid_counter"] = 101
        with self.assertRaisesRegex(ValueError, "cannot be added below"):
            create_board_proposal(
                board,
                title="Bad nesting",
                reason="Should fail",
                operations=[
                    {
                        "kind": "ADD_BRANCH",
                        "branch_kind": "circuit",
                        "parent_uid": "b101",
                        "values": {"description": "Invalid child"},
                    }
                ],
            )

    def test_update_operation_cannot_write_arbitrary_metadata(self):
        board = _board()
        board["branches"] = [
            {
                "uid": "b101",
                "kind": "final",
                "parent_key": "root",
                "circuit_id": "C-01",
                "description": "Existing load",
                "mode": "auto",
                "load_kw": 5.0,
                "phase": "three",
                "power_factor": 0.9,
                "demand_factor": 1.0,
                "material": "copper",
                "phase_preference": "Auto",
                "connection_option_id": None,
            }
        ]
        board["uid_counter"] = 101
        with self.assertRaisesRegex(ValueError, "Unsupported final proposal fields"):
            create_board_proposal(
                board,
                title="Unsafe update",
                reason="Should fail",
                operations=[
                    {
                        "kind": "UPDATE_BRANCH",
                        "target_uid": "b101",
                        "values": {"fault_source": {"kind": "NONE"}},
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
