import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_planner import FeederPhaseMappingDeclaration, calculate_board_hierarchy


class HierarchyPhaseMappingTests(unittest.TestCase):
    def _graph_with_unbalanced_child(self):
        graph = make_radial_board_graph(board_id="DB-ROOT", description="Root board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="F-CHILD",
            sub_board_id="DB-CHILD",
            description="Child board",
        )
        child_busbar = "F-CHILD:DB-CHILD:busbar"
        for circuit_id, description, load_kw, phase in (
            ("C-L1", "Child L1", 2.07, "L1"),
            ("C-L2", "Child L2", 4.14, "L2"),
            ("C-L3", "Child L3", 6.21, "L3"),
        ):
            graph = add_radial_circuit(
                graph,
                circuit_id=circuit_id,
                description=description,
                load_kw=load_kw,
                phase="single",
                power_factor=1.0,
                phase_preference=phase,
                parent_busbar_id=child_busbar,
            )
        return graph

    def test_identity_mapping_preserves_child_phase_labels_by_default(self):
        result = calculate_board_hierarchy(self._graph_with_unbalanced_child())
        child = result.plans_by_board_id["DB-CHILD"].phase_balance
        root = result.plans_by_board_id["DB-ROOT"].phase_balance
        self.assertAlmostEqual(root.l1_current_a, child.l1_current_a)
        self.assertAlmostEqual(root.l2_current_a, child.l2_current_a)
        self.assertAlmostEqual(root.l3_current_a, child.l3_current_a)
        contribution = result.plans_by_board_id["DB-ROOT"].request.phase_contributions[0]
        self.assertIn("Identity child-to-parent phase mapping", contribution.basis)

    def test_declared_phase_rotation_relabels_child_vector_at_parent_boundary(self):
        graph = self._graph_with_unbalanced_child()
        result = calculate_board_hierarchy(
            graph,
            feeder_phase_mappings=(
                FeederPhaseMappingDeclaration(
                    feeder_circuit_id="F-CHILD",
                    child_l1_to_parent="L2",
                    child_l2_to_parent="L3",
                    child_l3_to_parent="L1",
                    basis_note="Reviewed project phase rotation",
                ),
            ),
        )
        child = result.plans_by_board_id["DB-CHILD"].phase_balance
        root = result.plans_by_board_id["DB-ROOT"].phase_balance
        self.assertAlmostEqual(root.l1_current_a, child.l3_current_a)
        self.assertAlmostEqual(root.l2_current_a, child.l1_current_a)
        self.assertAlmostEqual(root.l3_current_a, child.l2_current_a)
        contribution = result.plans_by_board_id["DB-ROOT"].request.phase_contributions[0]
        self.assertIn("L1→L2, L2→L3, L3→L1", contribution.basis)
        self.assertIn("Reviewed project phase rotation", contribution.basis)
        feeder = result.feeder_rollups[0]
        self.assertTrue(any("declared mapping" in text.lower() for text in feeder.limitations))

    def test_phase_mapping_must_be_a_one_to_one_permutation(self):
        with self.assertRaisesRegex(ValueError, "one-to-one phase permutation"):
            calculate_board_hierarchy(
                self._graph_with_unbalanced_child(),
                feeder_phase_mappings=(
                    FeederPhaseMappingDeclaration(
                        "F-CHILD", "L1", "L1", "L3", "Invalid duplicate target"
                    ),
                ),
            )

    def test_phase_mapping_requires_provenance(self):
        with self.assertRaisesRegex(ValueError, "basis_note is required"):
            calculate_board_hierarchy(
                self._graph_with_unbalanced_child(),
                feeder_phase_mappings=(
                    FeederPhaseMappingDeclaration("F-CHILD", "L2", "L3", "L1", ""),
                ),
            )

    def test_duplicate_and_unknown_mapping_declarations_are_rejected(self):
        mapping = FeederPhaseMappingDeclaration(
            "F-CHILD", "L2", "L3", "L1", "Reviewed rotation"
        )
        with self.assertRaisesRegex(ValueError, "duplicate feeder phase mapping"):
            calculate_board_hierarchy(
                self._graph_with_unbalanced_child(),
                feeder_phase_mappings=(mapping, mapping),
            )
        with self.assertRaisesRegex(ValueError, "unknown sub-board feeder"):
            calculate_board_hierarchy(
                self._graph_with_unbalanced_child(),
                feeder_phase_mappings=(
                    FeederPhaseMappingDeclaration(
                        "F-UNKNOWN", "L2", "L3", "L1", "Reviewed rotation"
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
