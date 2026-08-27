import unittest
from pathlib import Path


class BoardPlannerUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (
            Path(__file__).resolve().parents[1] / "pages" / "3_Board_Planner.py"
        ).read_text(encoding="utf-8")

    def test_board_ui_uses_shared_backend_models(self):
        self.assertIn("BoardPlanRequest", self.text)
        self.assertIn("BoardPhasePreference", self.text)
        self.assertIn("calculate_board_plan", self.text)
        self.assertIn("CircuitDesignRequest", self.text)
        self.assertNotIn("calculate_design_current(", self.text)

    def test_board_ui_uses_dynamic_consumer_table(self):
        self.assertIn("st.data_editor(", self.text)
        self.assertIn('num_rows="dynamic"', self.text)
        self.assertIn('"Phase lock"', self.text)
        self.assertIn('["Auto", "L1", "L2", "L3"]', self.text)
        self.assertIn('["Single-phase", "Three-phase"]', self.text)

    def test_board_ui_uses_board_supply_voltage_contract(self):
        self.assertIn('"Line-line voltage (V)"', self.text)
        self.assertIn('"Line-neutral voltage (V)"', self.text)
        self.assertIn("line_to_line_voltage_v=float(voltage_ll)", self.text)
        self.assertIn("line_to_neutral_voltage_v=float(voltage_ln)", self.text)
        self.assertIn("voltage_v=float(voltage_ll if phase == \"three\" else voltage_ln)", self.text)

    def test_board_ui_hides_results_until_planning_and_invalidates_stale_result(self):
        self.assertIn('plan_board = st.button("Plan board"', self.text)
        self.assertIn('st.session_state["board_plan_result"]', self.text)
        self.assertIn('stored["signature"] != board_signature', self.text)
        self.assertIn("if stored:", self.text)

    def test_board_ui_surfaces_phase_and_incomer_outputs(self):
        self.assertIn('"Incomer candidate"', self.text)
        self.assertIn('"L1 planned current"', self.text)
        self.assertIn('"L2 planned current"', self.text)
        self.assertIn('"L3 planned current"', self.text)
        self.assertIn('"Phase spread"', self.text)
        self.assertIn("result.schedule_rows", self.text)

    def test_board_ui_keeps_scope_limitations_explicit(self):
        self.assertIn('with st.expander("Needs verification")', self.text)
        self.assertIn('with st.expander("Board planning assumptions")', self.text)
        self.assertIn("Board-level diversity", self.text)
        self.assertIn("final incomer protection verification", self.text)
        self.assertIn("load-balancing heuristic", self.text)

    def test_three_phase_phase_lock_is_rejected_before_backend_call(self):
        self.assertIn('phase == "three" and phase_lock != "Auto"', self.text)
        self.assertIn("phase lock only applies to single-phase circuits", self.text)


if __name__ == "__main__":
    unittest.main()
