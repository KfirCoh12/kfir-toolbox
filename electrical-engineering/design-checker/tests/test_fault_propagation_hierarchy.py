import unittest

from src.board_graph import make_radial_board_graph
from src.fault_propagation import CableFaultPath
from src.fault_propagation_hierarchy import relationship_fault_contexts
from src.protection_hierarchy import ProtectionRelationship


class FaultPropagationHierarchyTests(unittest.TestCase):
    def setUp(self):
        self.graph = make_radial_board_graph(
            board_id="MAIN-LV",
            description="Test board",
            line_to_line_voltage_v=400.0,
            line_to_neutral_voltage_v=230.0,
        )
        self.relationships = (
            ProtectionRelationship(
                upstream_node_id="incomer",
                downstream_node_id="F-01:device",
                downstream_circuit_id="F-01",
                upstream_rating_a=80.0,
                downstream_rating_a=80.0,
            ),
            ProtectionRelationship(
                upstream_node_id="F-01:device",
                downstream_node_id="C-01:device",
                downstream_circuit_id="C-01",
                upstream_rating_a=80.0,
                downstream_rating_a=80.0,
            ),
        )

    def test_root_pair_gets_main_busbar_fault(self):
        result = relationship_fault_contexts(
            self.graph,
            self.relationships,
            root_busbar_fault_current_ka=24.056,
        )
        self.assertAlmostEqual(result[0].prospective_fault_current_ka, 24.056)
        self.assertIsNone(result[0].path_circuit_id)
        self.assertIsNone(result[1].prospective_fault_current_ka)
        self.assertEqual(result[1].path_circuit_id, "F-01")

    def test_downstream_pair_uses_parent_protected_cable(self):
        result = relationship_fault_contexts(
            self.graph,
            self.relationships,
            root_busbar_fault_current_ka=24.056,
            cable_path_by_circuit_id={
                "F-01": CableFaultPath(
                    circuit_id="F-01",
                    material="copper",
                    cross_section_mm2=25.0,
                    parallel_runs=1,
                    length_m=30.0,
                )
            },
        )
        self.assertAlmostEqual(result[0].prospective_fault_current_ka, 24.056)
        self.assertIsNotNone(result[1].prospective_fault_current_ka)
        self.assertLess(result[1].prospective_fault_current_ka, 24.056)
        self.assertEqual(result[1].path_circuit_id, "F-01")
        self.assertIn("via F-01", result[1].basis)

    def test_missing_root_fault_stays_explicit(self):
        result = relationship_fault_contexts(
            self.graph,
            self.relationships,
            root_busbar_fault_current_ka=None,
        )
        self.assertIsNone(result[0].prospective_fault_current_ka)
        self.assertIn("main-board prospective fault current", result[0].missing_inputs)
        self.assertIsNone(result[1].prospective_fault_current_ka)


if __name__ == "__main__":
    unittest.main()
