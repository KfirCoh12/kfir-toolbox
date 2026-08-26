import unittest
from src.connection import get_connection_option, suggest_connection

class ConnectionTests(unittest.TestCase):
    def test_three_phase_40a_requirement_suggests_63a_connection(self):
        x=suggest_connection(phase="three",required_current_a=40)
        self.assertEqual(x.rating_a,63.0)
    def test_above_catalog_uses_fixed_connection(self):
        x=suggest_connection(phase="three",required_current_a=160)
        self.assertIsNone(x.rating_a)
        self.assertEqual(x.category,"fixed_connection")
    def test_option_lookup(self):
        self.assertEqual(get_connection_option("general_socket_16a_1ph").rating_a,16.0)
if __name__=="__main__": unittest.main()
