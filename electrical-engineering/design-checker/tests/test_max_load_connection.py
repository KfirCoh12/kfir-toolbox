import unittest
from src.max_load import MaxLoadInput, calculate_max_load

class MaxLoadConnectionTests(unittest.TestCase):
    def test_catalog_connection_can_be_limiting_constraint(self):
        r=calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,breaker_in_a=63,connection_option_id="industrial_32a_3ph"))
        self.assertEqual(r.limiting_constraint,"connection/outlet")
        self.assertEqual(r.max_current_a,32.0)
    def test_phase_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,connection_option_id="general_socket_16a_1ph"))
    def test_custom_and_catalog_connection_cannot_both_be_supplied(self):
        with self.assertRaises(ValueError):
            calculate_max_load(MaxLoadInput(voltage_v=400,phase="three",power_factor=0.9,connection_option_id="industrial_32a_3ph",connection_rating_a=32))
if __name__=="__main__": unittest.main()
