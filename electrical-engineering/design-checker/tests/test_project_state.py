import unittest

from src.project_state import (
    add_project_question,
    open_project_questions,
    project_revision,
    project_state_from_payload,
    record_project_fact,
    resolve_project_question,
)


class ProjectStateTests(unittest.TestCase):
    def test_legacy_board_starts_with_empty_revision_zero_state(self):
        state = project_state_from_payload({"board_id": "DB-01"})
        self.assertEqual(state["revision"], 0)
        self.assertEqual(state["facts"], {})
        self.assertEqual(state["questions"], [])
        self.assertEqual(state["proposals"], [])

    def test_fact_records_provenance_and_advances_revision(self):
        payload = {"board_id": "DB-01"}
        updated = record_project_fact(
            payload,
            key="occupancy.people",
            value=150,
            provenance="USER_PROVIDED",
            source_ref="chat",
            note="Approximate office occupancy",
        )
        self.assertEqual(project_revision(payload), 0)
        self.assertEqual(project_revision(updated), 1)
        fact = project_state_from_payload(updated)["facts"]["occupancy.people"]
        self.assertEqual(fact["value"], 150)
        self.assertEqual(fact["provenance"], "USER_PROVIDED")
        self.assertEqual(fact["source_ref"], "chat")

    def test_questions_are_prioritized_without_changing_design_revision(self):
        payload, deferred = add_project_question(
            {"board_id": "DB-01"},
            prompt="Breaker family?",
            priority="DEFERRED",
        )
        payload, blocking = add_project_question(
            payload,
            prompt="What is the available supply rating?",
            priority="BLOCKING",
            related_keys=("supply.rating_a",),
        )
        self.assertEqual(project_revision(payload), 0)
        questions = open_project_questions(payload)
        self.assertEqual(
            tuple(item["question_id"] for item in questions),
            (blocking, deferred),
        )

        resolved = resolve_project_question(
            payload,
            question_id=blocking,
            answer="400 A",
        )
        self.assertEqual(
            tuple(item["question_id"] for item in open_project_questions(resolved)),
            (deferred,),
        )
        self.assertEqual(project_revision(resolved), 0)

    def test_invalid_provenance_is_rejected(self):
        with self.assertRaises(ValueError):
            record_project_fact(
                {"board_id": "DB-01"},
                key="supply",
                value=400,
                provenance="AI_GUESS",
            )


if __name__ == "__main__":
    unittest.main()
