import unittest
from pathlib import Path

class UIScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=(Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    def test_secondary_ampacity_inputs_are_grouped_under_advanced(self):
        self.assertIn('with st.expander("Advanced cable conditions")', self.text)
        self.assertIn('Ambient air temperature (°C)', self.text)
        self.assertIn('Grouped circuits / cables', self.text)

    def test_secondary_voltage_drop_inputs_are_grouped_under_advanced(self):
        self.assertGreaterEqual(self.text.count('with st.expander("Advanced voltage-drop settings")'), 3)

    def test_product_specification_bloat_not_in_ui(self):
        for term in ("clock position", "IP degree", "identification colour", "interlocking"):
            self.assertNotIn(term, self.text.lower())

if __name__ == "__main__": unittest.main()
