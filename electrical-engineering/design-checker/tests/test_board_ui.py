import unittest
from pathlib import Path


class BoardPlannerUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.page = (root / "pages" / "3_Board_Planner.py").read_text(encoding="utf-8")
        cls.hmi = (root / "src" / "board_planner_hmi.py").read_text(encoding="utf-8")
        cls.state = (root / "src" / "board_planner_state.py").read_text(encoding="utf-8")

    def test_production_page_uses_hmi_workbench_and_shared_baseline(self):
        self.assertIn("render_board_planner", self.page)
        self.assertIn("ensure_office_working_baseline", self.page)
        self.assertNotIn("Workspace Preview", self.page)
        self.assertNotIn("HMI DESIGN PREVIEW", self.page)

    def test_hmi_uses_live_working_board_calculation_without_calculate_button(self):
        self.assertIn("calculate_working_board", self.hmi)
        self.assertIn("root_plan = calculated.hierarchy.root.plan", self.hmi)
        self.assertNotIn('st.button("Calculate board"', self.hmi)

    def test_hmi_layout_keeps_hierarchy_schedule_properties_above_full_width_sld(self):
        self.assertIn("st.columns([1.0, 1.65, 1.25]", self.hmi)
        self.assertIn("_render_hierarchy", self.hmi)
        self.assertIn("_render_schedule", self.hmi)
        self.assertIn("_render_properties", self.hmi)
        self.assertIn("render_hmi_single_line_svg", self.hmi)
        self.assertIn("height:650px", self.hmi)

    def test_hierarchy_is_collapsible_and_does_not_expose_device_or_cable_rows(self):
        self.assertIn("with st.expander", self.hmi)
        self.assertIn("_descendants", self.hmi)
        self.assertIn("Fields and sub-boards expand only when you need their circuits", self.hmi)
        self.assertNotIn('f"branch:{uid}:device"', self.hmi)
        self.assertNotIn('f"branch:{uid}:cable"', self.hmi)

    def test_context_aware_additions_support_circuit_field_and_sub_board(self):
        self.assertIn("_allowed_additions", self.hmi)
        self.assertIn('add_planner_branch(board, "circuit"', self.hmi)
        self.assertIn('add_planner_branch(board, "field"', self.hmi)
        self.assertIn('add_planner_branch(board, "sub_board"', self.hmi)
        self.assertIn("Only hierarchy-valid actions are shown", self.hmi)

    def test_structural_edits_are_persisted_through_owned_payload_boundary(self):
        self.assertIn("save_last_board(payload)", self.hmi)
        self.assertIn("payload = planner_owned_payload(board)", self.hmi)
        self.assertIn("_apply_and_save", self.hmi)
        self.assertIn("_PLANNER_OWNED_KEYS", self.state)
        self.assertNotIn('"fault_source"', self.state.split("_PLANNER_OWNED_KEYS", 1)[1].split(")", 1)[0])
        self.assertNotIn('"feeder_lengths_m"', self.state.split("_PLANNER_OWNED_KEYS", 1)[1].split(")", 1)[0])

    def test_board_voltage_and_identity_are_editable_in_inspector(self):
        self.assertIn('"Board ID"', self.hmi)
        self.assertIn('"Description"', self.hmi)
        self.assertIn('"L-L voltage (V)"', self.hmi)
        self.assertIn('"L-N voltage (V)"', self.hmi)
        self.assertIn('"Apply board changes"', self.hmi)

    def test_final_circuit_preserves_auto_and_manual_design_modes(self):
        self.assertIn('"Design mode", ["auto", "manual"]', self.hmi)
        self.assertIn("connection_options_for_phase", self.hmi)
        self.assertIn('"Connection / outlet"', self.hmi)
        self.assertIn('"connection_option_id"', self.hmi)
        self.assertIn('"Connected load (kW)"', self.hmi)

    def test_phase_preference_is_only_shown_for_single_phase(self):
        self.assertIn('if phase == "single":', self.hmi)
        self.assertIn('["Auto", "L1", "L2", "L3"]', self.hmi)
        self.assertIn('"Phase preference"', self.hmi)
        self.assertIn('"phase_preference": phase_pref if phase == "single" else "Auto"', self.hmi)

    def test_schedule_selection_drives_sld_route_focus(self):
        self.assertIn('selection_mode="single-row"', self.hmi)
        self.assertIn('"bp_hmi_focus_circuit_id"', self.hmi)
        self.assertIn("_route_graph_nodes", self.hmi)
        self.assertIn('selection_title = f"Route focus · {focus_circuit_id}"', self.hmi)

    def test_selected_subtree_can_be_removed(self):
        self.assertIn("remove_planner_branch_tree", self.hmi)
        self.assertIn('"Remove selected item"', self.hmi)
        self.assertIn("board[\"branches\"]", self.state)

    def test_live_kpis_surface_board_demand_and_unresolved_scope(self):
        self.assertIn("Max phase demand", self.hmi)
        self.assertIn("Incomer candidate", self.hmi)
        self.assertIn("Calculated branches", self.hmi)
        self.assertIn("Needs attention", self.hmi)

    def test_production_ui_keeps_protection_claims_out_of_planner(self):
        self.assertNotIn("VERIFIED", self.hmi)
        self.assertNotIn("selectivity", self.hmi.lower())
        self.assertIn("planning only", self.hmi)


if __name__ == "__main__":
    unittest.main()
