import unittest
from pathlib import Path


class UIScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (
            Path(__file__).resolve().parents[1] / "app.py"
        ).read_text(encoding="utf-8")

    def test_only_two_practical_workflows_are_exposed(self):
        self.assertIn(
            '["Design a supply", "Existing supply capacity"]',
            self.text,
        )
        self.assertNotIn('"Check an existing supply"', self.text)
        self.assertNotIn('"Find maximum load"', self.text)

    def test_existing_capacity_accepts_independent_known_components(self):
        section = self.text.split(
            'st.subheader("Existing supply capacity")', 1
        )[1]
        self.assertIn('"Breaker"', section)
        self.assertIn('"Cable"', section)
        self.assertIn('"Outlet / connection"', section)
        self.assertIn(
            "if not (use_breaker or use_cable or use_connection):",
            section,
        )
        self.assertIn(
            "breaker_in_a=breaker if use_breaker else None",
            section,
        )
        self.assertIn(
            "ampacity_route=route if use_cable else None",
            section,
        )
        self.assertIn("if use_connection", section)

    def test_existing_capacity_has_no_trial_load_input(self):
        section = self.text.split(
            'st.subheader("Existing supply capacity")', 1
        )[1]
        self.assertNotIn("Consumer load (kW)", section)
        self.assertIn("Maximum active load", section)
        self.assertIn("Still needs verification", section)

    def test_existing_capacity_progressively_reveals_optional_inputs(self):
        section = self.text.split(
            'st.subheader("Existing supply capacity")', 1
        )[1]
        self.assertIn('value=False,\n                key="cap_have_cable"', section)
        self.assertIn('if use_cable:', section)
        self.assertIn('if use_connection:', section)
        self.assertIn('if use_vd:', section)
        self.assertIn('help="Rated current printed on the breaker or protective device."', section)
        self.assertIn('help="Expected operating power factor of the load."', section)

    def test_existing_capacity_hides_stale_results_after_input_changes(self):
        section = self.text.split(
            'st.subheader("Existing supply capacity")', 1
        )[1]
        self.assertIn('st.session_state["capacity_result"]', section)
        self.assertIn(
            'stored_capacity_result["signature"] != capacity_signature',
            section,
        )
        self.assertIn('if stored_capacity_result:', section)
        self.assertNotIn(
            "Choose any component(s) you already know.",
            section,
        )

    def test_existing_capacity_keeps_result_detail_collapsed(self):
        section = self.text.split(
            'st.subheader("Existing supply capacity")', 1
        )[1]
        self.assertIn('with st.expander("Still needs verification")', section)
        self.assertIn('with st.expander("What sets the ceiling?")', section)
        self.assertIn('with st.expander("Verification notes")', section)
        self.assertIn('with st.expander("Calculation trace")', section)
        self.assertNotIn('expanded=True', section)

    def test_existing_capacity_renders_backend_verification_summary(self):
        section = self.text.split(
            'st.subheader("Existing supply capacity")', 1
        )[1]
        self.assertIn("summarize_max_load_verification(r)", section)
        self.assertIn('verification.scope_status == "NOT_VERIFIED"', section)
        self.assertIn('verification.scope_status == "PARTIAL_SCOPE"', section)
        self.assertIn("verification.blocking_issues", section)
        self.assertNotIn('if r.coverage_status == "FULL CORE COVERAGE"', section)

    def test_design_advanced_installation_conditions_do_not_surface_temperature_input(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        self.assertIn(
            'with st.expander("Advanced installation conditions")',
            design,
        )
        self.assertIn("Number of grouped circuits / cables", design)
        self.assertNotIn('st.selectbox("Ambient air temperature', design)
        self.assertIn("Method E · air · 30 °C", design)

    def test_design_parallel_runs_surface_explicit_verification_gates(self):
        self.assertIn("Parallel cable runs per phase", self.text)
        self.assertIn("acceptable current sharing", self.text)
        self.assertIn("parallel_runs=int(parallel_runs)", self.text)
        self.assertIn(
            "equal_current_sharing_confirmed=equal_current_sharing",
            self.text,
        )

    def test_design_supply_exposes_phase_without_bypassing_backend_guard(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        self.assertIn(
            '"Phase", ["Three-phase", "Single-phase"], key="design_phase"',
            design,
        )
        self.assertIn(
            'phase = "three" if phase_label == "Three-phase" else "single"',
            design,
        )
        self.assertIn("phase=phase", design)
        self.assertNotIn('phase="three"', design)
        self.assertIn(
            "Automatic cable sizing remains NOT VERIFIED",
            design,
        )
        self.assertIn("three loaded conductors only", design)

    def test_design_support_preflight_uses_backend_before_calculation(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        support_index = design.index("assess_installation_support")
        button_index = design.index("st.button(")
        self.assertLess(support_index, button_index)
        self.assertIn('copper_support.status == "SUPPORTED"', design)
        self.assertIn('aluminium_support.status == "SUPPORTED"', design)
        self.assertIn("missing_or_unsupported", design)
        self.assertIn("Cable auto-sizing: NOT VERIFIED", design)

    def test_design_support_preflight_uses_same_installation_inputs_as_selector(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        for field in (
            "phase=phase",
            "ambient_temperature_c=ambient",
            "grouped_circuits=grouped",
            "grouping_arrangement=arrangement",
            "parallel_runs=int(parallel_runs)",
            "equal_current_sharing_confirmed=equal_current_sharing",
        ):
            self.assertIn(field, design)

    def test_design_uses_compact_hover_help_for_technical_inputs(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        self.assertIn(
            'help="Input the expected load of the consumer."',
            design,
        )
        self.assertIn(
            "Fraction of the connected load expected to operate at the same time.",
            design,
        )
        self.assertIn(
            "Expected operating power factor of the load.",
            design,
        )
        self.assertIn(
            "Number of identical cables connected in parallel per phase.",
            design,
        )
        self.assertIn(
            "Total loaded circuits or cables installed together.",
            design,
        )
        self.assertIn(
            "Physical arrangement used for the grouping correction.",
            design,
        )
        self.assertIn(
            "Maximum voltage drop allowed by the project criterion.",
            design,
        )
        self.assertNotIn('help="System voltage', design)

    def test_design_progressively_reveals_voltage_drop_and_results(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        self.assertIn('"Check voltage drop"', design)
        self.assertIn("if check_vd:", design)
        self.assertNotIn("Start with the consumer kW", design)
        self.assertIn('st.session_state["design_result"]', design)
        self.assertIn(
            'stored_design_result["signature"] != design_signature',
            design,
        )
        self.assertIn('with st.expander("Why this suggestion?")', design)

    def test_design_renders_backend_verification_summary(self):
        design = self.text.split(
            'if mode == "Design a supply":', 1
        )[1].split(
            'else:\n    st.subheader("Existing supply capacity")', 1
        )[0]
        self.assertIn("summarize_circuit_selection_verification(r)", design)
        self.assertIn("verification.scope_status", design)
        self.assertIn("verification.blocking_issues", design)
        self.assertIn("issue.code", design)
        self.assertNotIn('if r.status == "SUGGESTION"', design)
        self.assertNotIn('elif r.status == "NO SUPPORTED SOLUTION"', design)

    def test_compact_field_width_is_enforced_in_ui_css(self):
        self.assertIn('[data-testid="stNumberInput"],', self.text)
        self.assertIn('[data-testid="stSelectbox"],', self.text)
        self.assertIn("max-width:260px;", self.text)

    def test_product_specification_bloat_not_in_ui(self):
        for term in (
            "clock position",
            "IP degree",
            "identification colour",
            "interlocking",
        ):
            self.assertNotIn(term, self.text.lower())

    def test_primary_inputs_live_in_main_workspace(self):
        self.assertNotIn("with st.sidebar:", self.text)
        self.assertGreaterEqual(
            self.text.count("with st.container(border=True):"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
