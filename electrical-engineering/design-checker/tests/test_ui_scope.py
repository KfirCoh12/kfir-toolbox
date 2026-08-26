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

    def test_existing_capacity_starts_from_hardware_not_trial_load(self):
        section=self.text.split('st.subheader("Existing supply capacity")',1)[1]
        self.assertIn('Existing breaker rating In (A)', section)
        self.assertIn('source_inputs("cap_")', section)
        self.assertNotIn('Consumer load (kW)', section)
        self.assertIn('Maximum active load', section)
        self.assertIn('Limiting factor', section)

    def test_design_advanced_cable_conditions_do_not_surface_temperature_input(self):
        design=self.text.split('if mode == "Design a supply":',1)[1].split('st.subheader("Existing supply capacity")',1)[0]
        self.assertIn('with st.expander("Advanced cable conditions")', design)
        self.assertIn('Number of grouped circuits / cables', design)
        self.assertNotIn('st.selectbox("Ambient air temperature', design)
        self.assertIn('30 °C reference condition', design)

    def test_product_specification_bloat_not_in_ui(self):
        for term in ("clock position", "IP degree", "identification colour", "interlocking"):
            self.assertNotIn(term, self.text.lower())

    def test_primary_inputs_live_in_main_workspace(self):
        self.assertNotIn("with st.sidebar:", self.text)
        self.assertGreaterEqual(self.text.count("with st.container(border=True):"), 2)

if __name__ == "__main__": unittest.main()
