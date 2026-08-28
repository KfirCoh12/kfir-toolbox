import unittest
from pathlib import Path


class BoardPlannerUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (
            Path(__file__).resolve().parents[1] / "pages" / "3_Board_Planner.py"
        ).read_text(encoding="utf-8")

    def test_board_ui_uses_hierarchy_native_backend(self):
        self.assertIn("make_radial_board_graph", self.text)
        self.assertIn("add_radial_circuit", self.text)
        self.assertIn("add_field_feeder", self.text)
        self.assertIn("add_sub_board_feeder", self.text)
        self.assertIn("board_plan_request_from_graph", self.text)
        self.assertIn("enrich_graph_with_plan", self.text)
        self.assertIn("calculate_board_plan", self.text)
        self.assertNotIn("calculate_design_current(", self.text)

    def test_board_ui_no_longer_uses_flat_data_editor_as_primary_model(self):
        self.assertNotIn("st.data_editor(", self.text)
        self.assertIn('st.markdown("### Electrical hierarchy")', self.text)
        self.assertIn('selected_node = st.radio(', self.text)
        self.assertIn('"＋ Add branch"', self.text)
        self.assertIn('"Delete selected branch"', self.text)
        self.assertIn('st.markdown("### Properties")', self.text)

    def test_new_board_starts_without_demo_branches(self):
        self.assertIn('def default_branches():', self.text)
        self.assertIn('"""Start a new board without demo branches."""', self.text)
        self.assertIn('return []', self.text)
        self.assertNotIn('"uid": "seed-1"', self.text)

    def test_branch_type_selector_exposes_final_field_and_sub_board(self):
        self.assertIn('"Final circuit"', self.text)
        self.assertIn('"Field / circuit group"', self.text)
        self.assertIn('"Sub-board"', self.text)
        self.assertIn('selected_parent_key is None', self.text)
        self.assertIn('parent_key', self.text)

    def test_nested_branches_are_added_under_selected_busbar(self):
        self.assertIn('busbar_by_parent_key = {"root": "busbar"}', self.text)
        self.assertIn('parent_busbar_id=parent_busbar_id', self.text)
        self.assertIn('token_to_parent_key[f"branch:{uid}:busbar"] = uid', self.text)
        self.assertIn('append_tree(uid, depth + 1)', self.text)

    def test_board_ui_builds_live_sld_before_calculation(self):
        self.assertIn("render_board_graph_svg", self.text)
        self.assertIn("components.html(svg", self.text)
        self.assertIn('st.markdown("### Live single-line diagram")', self.text)
        self.assertIn("display_graph = draft_graph", self.text)
        self.assertIn("if stored:", self.text)
        self.assertIn("display_graph = enrich_graph_with_plan", self.text)

    def test_board_ui_uses_board_supply_voltage_contract(self):
        self.assertIn('"Line-line voltage (V)"', self.text)
        self.assertIn('"Line-neutral voltage (V)"', self.text)
        self.assertIn("line_to_line_voltage_v=float(voltage_ll)", self.text)
        self.assertIn("line_to_neutral_voltage_v=float(voltage_ln)", self.text)

    def test_calculation_enriches_live_model_and_invalidates_when_inputs_change(self):
        self.assertIn('calculate = st.button("Calculate board"', self.text)
        self.assertIn('st.session_state["tree_board_plan"]', self.text)
        self.assertIn('stored["signature"] != signature', self.text)
        self.assertIn('st.session_state.pop("tree_board_plan", None)', self.text)

    def test_schedule_is_generated_secondary_view(self):
        self.assertIn('with st.expander("Generated circuit schedule")', self.text)
        self.assertIn("result.schedule_rows", self.text)
        self.assertNotIn('st.markdown("### Circuit schedule")', self.text)

    def test_board_ui_surfaces_phase_and_incomer_outputs(self):
        self.assertIn('m1.metric(', self.text)
        self.assertIn('"Incomer"', self.text)
        self.assertIn('m2.metric("L1"', self.text)
        self.assertIn('m3.metric("L2"', self.text)
        self.assertIn('m4.metric("L3"', self.text)
        self.assertIn('m5.metric("Spread"', self.text)

    def test_board_ui_keeps_new_hierarchy_limitations_explicit(self):
        self.assertIn('with st.expander("Needs verification")', self.text)
        self.assertIn('with st.expander("Board planning assumptions")', self.text)
        self.assertIn("Field feeder aggregation", self.text)
        self.assertIn("sub-board feeder demand", self.text)
        self.assertIn("final incomer protection verification", self.text)

    def test_phase_preference_is_only_exposed_for_single_phase_nodes(self):
        self.assertIn('if new_phase == "single":', self.text)
        self.assertIn('"Phase assignment"', self.text)
        self.assertIn('["Auto", "L1", "L2", "L3"]', self.text)


if __name__ == "__main__":
    unittest.main()
