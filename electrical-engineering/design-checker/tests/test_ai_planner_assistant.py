import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.ai_planner_assistant import (
    api_key_configured,
    configured_model,
    run_assistant_turn,
)
from src.board_persistence import load_last_board, save_last_board


class _FakeResponses:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("Unexpected extra Responses API call")
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses):
        self.responses = _FakeResponses(responses)


def _usage(input_tokens, output_tokens):
    return SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)


def _function_response(response_id, name, arguments, call_id="call-1"):
    return SimpleNamespace(
        id=response_id,
        output=[
            SimpleNamespace(
                type="function_call",
                name=name,
                arguments=json.dumps(arguments),
                call_id=call_id,
            )
        ],
        usage=_usage(100, 20),
        output_text="",
    )


def _text_response(response_id, text):
    return SimpleNamespace(
        id=response_id,
        output=[],
        usage=_usage(80, 40),
        output_text=text,
    )


class AIPlannerAssistantTests(unittest.TestCase):
    def _seed(self, path: Path):
        save_last_board(
            {
                "board_id": "DB-01",
                "description": "AI test board",
                "line_to_line_voltage_v": 400.0,
                "line_to_neutral_voltage_v": 230.0,
                "branches": [],
                "uid_counter": 100,
                "selected_node": "busbar",
            },
            path,
        )

    def test_api_key_and_model_configuration(self):
        self.assertFalse(api_key_configured({}))
        self.assertTrue(api_key_configured({"OPENAI_API_KEY": "sk-test"}))
        self.assertEqual(configured_model({}), "gpt-5.6-terra")
        self.assertEqual(
            configured_model({"OPENAI_PLANNER_MODEL": "gpt-5.6-sol"}),
            "gpt-5.6-sol",
        )

    def test_model_tool_catalog_withholds_apply_and_reject(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)
            client = _FakeClient([_text_response("r1", "Ready.")])

            run_assistant_turn("Review this board", client=client, path=path)
            tools = client.responses.calls[0]["tools"]
            names = {tool["name"] for tool in tools}
            self.assertIn("create_board_proposal", names)
            self.assertIn("preview_board_proposal", names)
            self.assertNotIn("apply_board_proposal", names)
            self.assertNotIn("reject_board_proposal", names)

    def test_tool_loop_records_fact_and_creates_non_destructive_proposal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)
            client = _FakeClient(
                [
                    _function_response(
                        "r1",
                        "record_fact",
                        {
                            "key": "occupancy.people",
                            "value": 150,
                            "provenance": "USER_PROVIDED",
                        },
                    ),
                    _function_response(
                        "r2",
                        "create_board_proposal",
                        {
                            "title": "Add general power circuit",
                            "reason": "Start a preliminary office board concept.",
                            "operations": [
                                {
                                    "kind": "ADD_BRANCH",
                                    "branch_kind": "circuit",
                                    "parent_uid": "root",
                                    "values": {
                                        "circuit_id": "GP-01",
                                        "description": "Workstation sockets",
                                        "phase": "single",
                                        "load_kw": 3.0,
                                    },
                                }
                            ],
                            "assumptions": [
                                "Workstation grouping is provisional."
                            ],
                        },
                        call_id="call-2",
                    ),
                    _text_response(
                        "r3",
                        "I recorded the occupancy and created proposal P-001 for review.",
                    ),
                ]
            )

            result = run_assistant_turn(
                "We have about 150 people. Start the board.",
                client=client,
                path=path,
            )

            self.assertEqual(
                result.text,
                "I recorded the occupancy and created proposal P-001 for review.",
            )
            self.assertEqual(
                result.tool_calls,
                ("record_fact", "create_board_proposal"),
            )
            self.assertEqual(result.input_tokens, 280)
            self.assertEqual(result.output_tokens, 80)

            persisted = load_last_board(path)
            self.assertEqual(persisted["branches"], [])
            state = persisted["project_state"]
            self.assertEqual(state["facts"]["occupancy.people"]["value"], 150)
            self.assertEqual(state["proposals"][0]["status"], "PENDING")
            self.assertEqual(state["proposals"][0]["proposal_id"], "P-001")

            first = client.responses.calls[0]
            self.assertIn("CURRENT PLANNER PROJECT SNAPSHOT", first["input"])
            self.assertIn("150 people", first["input"])
            self.assertFalse(first["parallel_tool_calls"])
            self.assertEqual(first["reasoning"]["effort"], "low")
            self.assertEqual(client.responses.calls[1]["previous_response_id"], "r1")
            self.assertEqual(client.responses.calls[2]["previous_response_id"], "r2")

    def test_existing_response_id_is_used_for_multi_turn_context(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)
            client = _FakeClient([_text_response("new", "Updated.")])

            result = run_assistant_turn(
                "Continue",
                previous_response_id="previous",
                client=client,
                path=path,
            )

            self.assertEqual(result.response_id, "new")
            self.assertEqual(
                client.responses.calls[0]["previous_response_id"],
                "previous",
            )

    def test_tool_failure_is_returned_to_model_instead_of_mutating_board(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "last_board.json"
            self._seed(path)
            client = _FakeClient(
                [
                    _function_response(
                        "r1",
                        "create_board_proposal",
                        {
                            "title": "Invalid",
                            "reason": "Should be rejected by Planner.",
                            "operations": [
                                {
                                    "kind": "UPDATE_BOARD",
                                    "values": {"not_allowed": 1},
                                }
                            ],
                        },
                    ),
                    _text_response("r2", "The proposed change was not valid."),
                ]
            )

            result = run_assistant_turn(
                "Change the board.",
                client=client,
                path=path,
            )

            self.assertEqual(result.text, "The proposed change was not valid.")
            tool_output = client.responses.calls[1]["input"][0]
            decoded = json.loads(tool_output["output"])
            self.assertFalse(decoded["ok"])
            self.assertIn("Unsupported board proposal fields", decoded["error"])
            self.assertEqual(load_last_board(path)["branches"], [])


if __name__ == "__main__":
    unittest.main()
