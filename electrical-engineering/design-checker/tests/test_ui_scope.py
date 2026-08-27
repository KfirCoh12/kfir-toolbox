import unittest
from pathlib import Path

class UIScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=(Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    def test_only_two_practical_workflows_are_exposed(self):
        self.assertIn('["Design a supply", "Existing supply capacity"]', self.text)
        self.assertNotIn('"Check an existing supply"', self.text)
        self.assertNotIn('"Find maximum load"', self.text)

    def test_existing_capacity_accepts_independent_known_components(self):
        section=self.text.split('st.subheader("Existing supply capacity")',1)[1]
        self.assertIn('I have a breaker rating', section)
        self.assertIn('I have an existing cable', section)
        self.assertIn('I have an outlet / connection rating', section)
        self.assertIn('if not (use_breaker or use_cable or use_connection):', section)
        self.assertIn('breaker_in_a=breaker if use_breaker else None', section)
        self.assertIn('ampacity_route=route if use_cable else None', section)
        self.assertIn('connection_option_id=connection_option_id if use_connection else None', section)

    def test_existing_capacity_has_no_trial_load_input(self):
        section=self.text.split('st.subheader("Existing supply capacity")',1)[1]
        self.assertNotIn('Consumer load (kW)', section)
        self.assertIn('Maximum active load', section)
        self.assertIn('Still needs verification', section)

    def test_design_advanced_cable_conditions_do_not_surface_temperature_input(self):
        design=self.text.split('if mode == "Design a supply":',1)[1].split('else:\n    st.subheader("Existing supply capacity")',1)[0]
        self.assertIn('with st.expander("Advanced cable conditions")', design)
        self.assertIn('Number of grouped circuits / cables', design)
        self.assertNotIn('st.selectbox("Ambient air temperature', design)
        self.assertIn('30 Â°C reference condition', design)


    def test_design_supply_exposes_phase_without_bypassing_backend_guard(self):
        design=self.text.split('if mode == "Design a supply":',1)[1].split('else:\n    st.subheader("Existing supply capacity")',1)[0]
        self.assertIn('st.selectbox("Phase", ["Three-phase", "Single-phase"], key="design_phase")', design)
        self.assertIn('phase = "three" if phase_label == "Three-phase" else "single"', design)
        self.assertIn('phase=phase', design)
        self.assertNotIn('phase="three"', design)
        self.assertIn('Automatic cable sizing remains NOT VERIFIED', design)
        self.assertIn('three loaded conductors only', design)

    def test_product_specification_bloat_not_in_ui(self):
        for term in ("clock position", "IP degree", "identification colour", "interlocking"):
            self.assertNotIn(term, self.text.lower())

    def test_primary_inputs_live_in_main_workspace(self):
        self.assertNotIn("with st.sidebar:", self.text)
        self.assertGreaterEqual(self.text.count("with st.container(border=True):"), 2)

if __name__ == "__main__": unittest.main()
