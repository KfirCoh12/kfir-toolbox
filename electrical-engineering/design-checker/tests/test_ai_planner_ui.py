import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "pages" / "5_AI_Board_Assistant.py").read_text(encoding="utf-8")
ADAPTER = (ROOT / "src" / "ai_planner_assistant.py").read_text(encoding="utf-8")


class AIPlannerUITests(unittest.TestCase):
    def test_page_requires_api_key_without_exposing_it(self):
        self.assertIn("api_key_configured()", PAGE)
        self.assertIn("OPENAI_API_KEY is not available", PAGE)
        self.assertNotIn("st.text_input("API", PAGE)
        self.assertNotIn("st.text_area("API", PAGE)

    def test_chat_reads_live_project_and_routes_board_review_to_planner(self):
        self.assertIn("snapshot = get_project()", PAGE)
        self.assertIn("Open Board Planner", PAGE)
        self.assertIn("Pending proposals", PAGE)
        self.assertIn("Project facts", PAGE)
        self.assertIn("Open questions", PAGE)

    def test_model_cannot_approve_its_own_changes(self):
        self.assertIn('"create_board_proposal"', ADAPTER)
        self.assertIn('"preview_board_proposal"', ADAPTER)
        model_tool_section = ADAPTER.split("_MODEL_TOOL_NAMES =", 1)[1].split("}", 1)[0]
        self.assertNotIn("apply_board_proposal", model_tool_section)
        self.assertNotIn("reject_board_proposal", model_tool_section)
        self.assertIn("It cannot directly approve its own board changes.", PAGE)

    def test_chat_keeps_multi_turn_response_id_in_session(self):
        self.assertIn("ai_board_previous_response_id", PAGE)
        self.assertIn("previous_response_id=", PAGE)
        self.assertIn("result.response_id", PAGE)

    def test_default_model_is_cost_balanced_terra(self):
        self.assertIn('_DEFAULT_MODEL = "gpt-5.6-terra"', ADAPTER)
        self.assertIn('reasoning": {"effort": configured_reasoning()}', ADAPTER)


if __name__ == "__main__":
    unittest.main()
