import unittest
from pathlib import Path


class BoardPlannerUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (
            Path(__file__).resolve().parents[1] / "pages" / "3_Board_Planner.py"
        ).read_text(encoding="utf-8")

    def test_board_ui_uses_hierarchy_and_branch_engines(self):
        self.assertIn("make_radial_board_graph", self.text)
        self.assertIn("add_radial_circuit", self.text)
        self.assertIn("add_field_feeder", self.text)
        self.assertIn("add_sub_board_feeder", self.text)
        self.assertIn("enrich_graph_with_plan", self.text)
        self.assertIn("FinalBranchDesignRequest", self.text)
        self.assertIn("calculate_final_branch", self.text)
        self.assertIn("calculate_board_plan", self.text)
        self.assertNotIn("calculate_design_current(", self.text)

    def test_board_ui_uses_structure_and_properties_side_by_side(self):
        self.assertNotIn("st.data_editor(", self.text)
        self.assertIn('workspace_left, workspace_right = st.columns(', self.text)
        self.assertIn('st.markdown("### Board structure")', self.text)
        self.assertIn('st.markdown("### Properties")', self.text)
        self.assertIn('selected_node = st.radio(', self.text)
        self.assertIn('"＋ Add"', self.text)
        self.assertIn('"Delete selected"', self.text)

    def test_new_board_starts_without_demo_branches(self):
        self.assertIn('def default_branches():', self.text)
        self.assertIn('"""Start a new board without demo branches."""', self.text)
        self.assertIn('return []', self.text)
        self.assertNotIn('"uid": "seed-1"', self.text)

    def test_board_identity_requires_explicit_edit_and_rejects_blank_commit(self):
        self.assertIn('identity_editing = bool(st.session_state.get("tree_identity_editing", False))', self.text)
        self.assertIn('st.button("Edit identity"', self.text)
        self.assertIn('st.button("Save identity"', self.text)
        self.assertIn('st.button("Cancel"', self.text)
        self.assertIn('disabled=True, key="tree_board_id_locked"', self.text)
        self.assertIn('disabled=True, key="tree_board_description_locked"', self.text)
        self.assertIn('if not clean_board_id or not clean_description:', self.text)
        self.assertIn('Existing board identity was kept unchanged', self.text)
        self.assertIn('"board_id": board_id', self.text)
        self.assertIn('"description": description', self.text)

    def test_branch_type_selector_exposes_final_field_and_sub_board(self):
        self.assertIn('"Final circuit"', self.text)
        self.assertIn('"Field / circuit group"', self.text)
        self.assertIn('"Sub-board"', self.text)
        self.assertIn('selected_parent_key is None', self.text)
        self.assertIn('parent_key', self.text)

    def test_user_hierarchy_does_not_expose_protection_or_cable_as_rows(self):
        self.assertNotIn('f"branch:{uid}:device"', self.text)
        self.assertNotIn('f"branch:{uid}:cable"', self.text)
        self.assertIn('token = f"branch:{uid}"', self.text)
        self.assertIn("Live derived branch", self.text)

    def test_field_and_sub_board_are_direct_add_targets(self):
        self.assertIn('token_to_parent_key[token] = uid', self.text)
        self.assertIn('append_tree(uid, depth + 1, own_group)', self.text)
        self.assertIn('busbar_by_parent_key = {"root": "busbar"}', self.text)
        self.assertIn('parent_busbar_id=parent_busbar_id', self.text)

    def test_field_families_have_visual_markers(self):
        self.assertIn('("🟩", "🟢")', self.text)
        self.assertIn('("🟦", "🔵")', self.text)
        self.assertIn('group_by_uid', self.text)
        self.assertIn('inherited_group', self.text)

    def test_board_ui_builds_fit_to_view_sld_below_workspace(self):
        self.assertIn("render_board_graph_svg", self.text)
        self.assertIn('st.markdown("### Live single-line diagram")', self.text)
        self.assertIn('diagram_html = f\'<div style="width:100%;height:650px;', self.text)
        self.assertIn('components.html(diagram_html, height=670, scrolling=False)', self.text)
        self.assertIn("display_graph = draft_graph", self.text)
        self.assertIn("display_graph = enrich_graph_with_plan", self.text)

    def test_list_selection_is_reflected_in_diagram_highlight(self):
        self.assertIn('def selected_graph_nodes(', self.text)
        self.assertIn('highlighted = selected_graph_nodes(selected_node, selected_branch)', self.text)
        self.assertIn('render_board_graph_svg(display_graph, highlighted)', self.text)

    def test_board_ui_uses_board_supply_voltage_contract(self):
        self.assertIn('"Line-line voltage (V)"', self.text)
        self.assertIn('"Line-neutral voltage (V)"', self.text)
        self.assertIn("line_to_line_voltage_v=float(voltage_ll)", self.text)
        self.assertIn("line_to_neutral_voltage_v=float(voltage_ln)", self.text)

    def test_final_circuit_exposes_live_auto_manual_modes(self):
        self.assertIn('"Auto from load"', self.text)
        self.assertIn('"Manual from outlet"', self.text)
        self.assertIn('"Outlet / connection"', self.text)
        self.assertIn("connection_options_for_phase", self.text)
        self.assertIn('mode=mode', self.text)
        self.assertIn('connection_option_id=branch.get("connection_option_id")', self.text)

    def test_manual_mode_uses_current_basis_without_inventing_kw(self):
        self.assertIn('graph_load_kw = None', self.text)
        self.assertIn('display_detail = f"Manual · {preview.connection_rating_a:g} A outlet"', self.text)
        self.assertIn('Manual outlet mode fixes the rated outlet current as the branch requirement', self.text)

    def test_live_board_calculation_replaces_calculate_button(self):
        self.assertIn('def build_live_root_request(', self.text)
        self.assertIn('circuits.append(result.circuit.request)', self.text)
        self.assertIn('live_plan = calculate_board_plan(root_request)', self.text)
        self.assertNotIn('st.button("Calculate board"', self.text)
        self.assertNotIn('tree_board_plan', self.text)

    def test_field_properties_show_bottom_up_feeder_rollup(self):
        self.assertIn("calculate_field_rollups", self.text)
        self.assertIn("enrich_graph_with_field_rollups", self.text)
        self.assertIn('"Feeder conductor material"', self.text)
        self.assertIn("Live field roll-up", self.text)
        self.assertIn('f1.metric("Max phase"', self.text)
        self.assertIn('"Feeder breaker"', self.text)
        self.assertIn('f3.metric("Feeder cable"', self.text)
        self.assertIn("No additional field diversity is applied", self.text)

    def test_field_rollup_does_not_replace_root_child_circuit_accounting(self):
        self.assertIn('field_rollups = calculate_field_rollups(draft_graph, live_plan, field_materials())', self.text)
        self.assertIn('display_graph = enrich_graph_with_field_rollups(display_graph, field_rollups)', self.text)
        self.assertNotIn('circuits.append(rollup.feeder_design.request)', self.text)

    def test_sub_board_children_are_not_flattened_into_root_live_plan(self):
        self.assertIn('def is_below_sub_board(', self.text)
        self.assertIn('if branch.get("kind") != "final" or is_below_sub_board(branch):', self.text)

    def test_schedule_is_generated_secondary_view(self):
        self.assertIn('with st.expander("Generated circuit schedule")', self.text)
        self.assertIn("live_plan.schedule_rows", self.text)
        self.assertNotIn('st.markdown("### Circuit schedule")', self.text)

    def test_board_ui_surfaces_live_phase_and_incomer_outputs(self):
        self.assertIn('st.markdown("### Live board summary")', self.text)
        self.assertIn('m1.metric("Provisional incomer"', self.text)
        self.assertIn('m2.metric("L1"', self.text)
        self.assertIn('m3.metric("L2"', self.text)
        self.assertIn('m4.metric("L3"', self.text)
        self.assertIn('m5.metric("Spread"', self.text)

    def test_board_ui_keeps_hierarchy_limitations_explicit(self):
        self.assertIn('with st.expander("Current calculation scope / checks")', self.text)
        self.assertIn('with st.expander("Branches needing input")', self.text)
        self.assertIn("Field feeders now roll up their calculated child phase currents", self.text)
        self.assertIn("neutral loading and harmonic effects", self.text)
        self.assertIn("Sub-board feeder demand", self.text)
        self.assertIn("final protection verification", self.text)

    def test_phase_preference_is_only_exposed_for_single_phase_nodes(self):
        self.assertIn('if new_phase == "single":', self.text)
        self.assertIn('"Phase assignment"', self.text)
        self.assertIn('["Auto", "L1", "L2", "L3"]', self.text)


if __name__ == "__main__":
    unittest.main()
