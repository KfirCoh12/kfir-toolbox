import unittest
from src.circuit_selector import CircuitSelectionInput, select_circuit

class SelectorConnectionTests(unittest.TestCase):
    def test_forward_selector_includes_connection_suggestion(self):
        r=select_circuit(CircuitSelectionInput(load_type="kw",load_value=30,voltage_v=400,phase="three",power_factor=0.9,demand_factor=0.8,connection_requires_neutral=True))
        self.assertEqual(r.suggested_breaker_a,40.0)
        self.assertIsNotNone(r.suggested_connection)
        self.assertEqual(r.suggested_connection.rating_a,63.0)
        self.assertTrue(any("connection" in x.lower() for x in r.limitations))
        self.assertIsNotNone(r.suggested_connection_configuration)
        self.assertEqual(r.suggested_connection_configuration.poles,"3P+N+E")
        self.assertEqual(r.suggested_connection_configuration.clock_position_h,6)
if __name__=="__main__": unittest.main()
