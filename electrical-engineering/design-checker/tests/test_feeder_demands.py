import unittest

from src.board_boundaries import calculation_boundaries_from_graph
from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.board_planner import calculate_board_plan
from src.board_summaries import board_hierarchy_summaries
from src.feeder_demands import FeederDemandDeclaration, feeder_demand_contracts


class FeederDemandContractTests(unittest.TestCase):
    def _nested_graph(self):
        graph = add_sub_board_feeder(
            make_radial_board_graph(board_id="MDB", description="Main board"),
            feeder_id="F-01",
            sub_board_id="DB-L1",
            description="Level 1 board",
        )
        return add_radial_circuit(
            graph,
            circuit_id="L1-C01",
            description="Child load",
            phase="three",
            load_kw=18.0,
            parent_busbar_id="F-01:DB-L1:busbar",
        )

    def test_uncalculated_child_waits_for_local_calculation(self):
        summaries = board_hierarchy_summaries(self._nested_graph())
        root, child = feeder_demand_contracts(summaries)
        self.assertEqual(root.status, "ROOT_BOARD")
        self.assertEqual(child.status, "WAITING_FOR_LOCAL_CALCULATION")
        self.assertFalse(child.local_calculation_available)
        self.assertIsNone(child.local_max_phase_current_reference_a)
        self.assertIsNone(child.declared_demand_current_a)

    def test_local_current_is_reference_only_and_not_silently_promoted_to_feeder_demand(self):
        graph = self._nested_graph()
        child_boundary = calculation_boundaries_from_graph(graph)[1]
        child_plan = calculate_board_plan(child_boundary.request)
        summaries = board_hierarchy_summaries(graph, (child_plan,))
        root, child = feeder_demand_contracts(summaries)

        self.assertEqual(root.status, "ROOT_BOARD")
        self.assertEqual(child.status, "AWAITING_DEMAND_INPUT")
        self.assertTrue(child.local_calculation_available)
        self.assertAlmostEqual(
            child.local_max_phase_current_reference_a,
            child_plan.phase_balance.max_phase_current_a,
        )
        self.assertIsNone(child.declared_demand_current_a)
        self.assertFalse(child.has_declared_demand)

    def test_explicit_declaration_records_value_and_provenance_without_calculating_it(self):
        graph = self._nested_graph()
        child_boundary = calculation_boundaries_from_graph(graph)[1]
        child_plan = calculate_board_plan(child_boundary.request)
        summaries = board_hierarchy_summaries(graph, (child_plan,))
        contracts = feeder_demand_contracts(
            summaries,
            (
                FeederDemandDeclaration(
                    board_id="DB-L1",
                    demand_current_a=24.0,
                    basis="USER_DECLARED",
                    basis_note="Engineer-entered feeder demand for planning",
                ),
            ),
        )
        child = contracts[1]
        self.assertEqual(child.status, "DEMAND_DECLARED")
        self.assertEqual(child.declared_demand_current_a, 24.0)
        self.assertEqual(child.declaration_basis, "USER_DECLARED")
        self.assertEqual(
            child.declaration_note,
            "Engineer-entered feeder demand for planning",
        )
        self.assertTrue(child.has_declared_demand)

    def test_declaration_requires_valid_current_and_provenance(self):
        summaries = board_hierarchy_summaries(self._nested_graph())
        with self.assertRaisesRegex(ValueError, "greater than 0"):
            feeder_demand_contracts(
                summaries,
                (FeederDemandDeclaration("DB-L1", 0.0, "USER_DECLARED", "manual"),),
            )
        with self.assertRaisesRegex(ValueError, "basis_note is required"):
            feeder_demand_contracts(
                summaries,
                (FeederDemandDeclaration("DB-L1", 20.0, "USER_DECLARED", ""),),
            )

    def test_root_foreign_and_duplicate_declarations_are_rejected(self):
        summaries = board_hierarchy_summaries(self._nested_graph())
        with self.assertRaisesRegex(ValueError, "root board"):
            feeder_demand_contracts(
                summaries,
                (FeederDemandDeclaration("MDB", 50.0, "USER_DECLARED", "manual"),),
            )
        with self.assertRaisesRegex(ValueError, "not in hierarchy summaries"):
            feeder_demand_contracts(
                summaries,
                (FeederDemandDeclaration("OTHER", 20.0, "USER_DECLARED", "manual"),),
            )
        declaration = FeederDemandDeclaration(
            "DB-L1", 20.0, "USER_DECLARED", "manual"
        )
        with self.assertRaisesRegex(ValueError, "duplicate feeder demand declaration"):
            feeder_demand_contracts(summaries, (declaration, declaration))


if __name__ == "__main__":
    unittest.main()
