import unittest
from src.connection import IEC_60309_SOURCES, get_connection_option, suggest_connection

class ConnectionTests(unittest.TestCase):
    def test_three_phase_40a_requirement_suggests_63a_connection(self):
        x=suggest_connection(phase="three",required_current_a=40)
        self.assertEqual(x.rating_a,63.0)
        self.assertEqual(x.category,"industrial_socket")

    def test_above_catalog_uses_fixed_connection(self):
        x=suggest_connection(phase="three",required_current_a=160)
        self.assertIsNone(x.rating_a)
        self.assertEqual(x.category,"fixed_connection")

    def test_industrial_option_keeps_iec_rating_provenance(self):
        x=get_connection_option("industrial_32a_3ph")
        standards={s.standard for s in x.evidence_sources}
        self.assertIn("IEC 60309-1:2021/COR1:2023",standards)
        self.assertIn("IEC 60309-2:2021/COR1:2026",standards)

    def test_public_iec_rating_series_used_by_catalog(self):
        ratings=[get_connection_option(f"industrial_{a}a_3ph").rating_a for a in (16,32,63,125)]
        self.assertEqual(ratings,[16.0,32.0,63.0,125.0])

    def test_connection_model_contains_only_calculation_relevant_choice_fields(self):
        x=get_connection_option("industrial_32a_3ph")
        self.assertEqual(x.phase,"three")
        self.assertEqual(x.rating_a,32.0)
        for field in ("clock_position_h","identification_colour","frequency_hz","voltage_range_v","ip_rating"):
            self.assertFalse(hasattr(x,field),field)

    def test_general_socket_is_not_mislabeled_as_iec_60309(self):
        x=get_connection_option("general_socket_16a_1ph")
        self.assertFalse(x.evidence_sources)

    def test_source_metadata_is_backend_provenance(self):
        self.assertEqual(len(IEC_60309_SOURCES),2)

if __name__=="__main__": unittest.main()
