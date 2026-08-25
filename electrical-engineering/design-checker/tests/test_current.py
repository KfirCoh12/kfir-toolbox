import math, unittest
from src.current import calculate_design_current

class DesignCurrentTests(unittest.TestCase):
    def test_three_phase_kw(self):
        r=calculate_design_current(load_type="kw",load_value=97,voltage_v=400,phase="three",power_factor=0.9)
        self.assertAlmostEqual(r.design_current_a,97000/(math.sqrt(3)*400*.9),places=6)
    def test_office_shortcut_close(self):
        r=calculate_design_current(load_type="kw",load_value=97,voltage_v=400,phase="three",power_factor=.9)
        shortcut=97*1.6; self.assertLess(abs(r.design_current_a-shortcut)/shortcut,.01)
    def test_margin_separate(self):
        r=calculate_design_current(load_type="kw",load_value=97,voltage_v=400,phase="three",power_factor=.9,design_margin=.8)
        self.assertAlmostEqual(r.margin_adjusted_current_a,r.design_current_a/.8,places=6)
        self.assertEqual(r.standards_status,"CALCULATED — NOT IEC VERIFIED")
    def test_three_phase_kva(self):
        r=calculate_design_current(load_type="kva",load_value=100,voltage_v=400,phase="three")
        self.assertAlmostEqual(r.design_current_a,100000/(math.sqrt(3)*400),places=6)
    def test_single_phase_kw(self):
        r=calculate_design_current(load_type="kw",load_value=5,voltage_v=230,phase="single",power_factor=.95)
        self.assertAlmostEqual(r.design_current_a,5000/(230*.95),places=6)
    def test_direct_current_demand(self):
        r=calculate_design_current(load_type="a",load_value=100,demand_factor=.8); self.assertEqual(r.design_current_a,80)
    def test_missing_pf_not_guessed(self):
        with self.assertRaises(ValueError): calculate_design_current(load_type="kw",load_value=10,voltage_v=400,phase="three")

if __name__ == "__main__": unittest.main()
