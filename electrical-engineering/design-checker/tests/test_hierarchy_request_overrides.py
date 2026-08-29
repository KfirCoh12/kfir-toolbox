import unittest

from src.board_boundaries import calculation_boundaries_from_graph
from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.circuit_engine import CircuitDesignRequest
from src.hierarchy_planner import calculate_board_hierarchy


class HierarchyRequestOverrideTests(unittest.TestCase):
    def _base_graph(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Downstream board",
        )
        return graph

    def test_fixed_current_override_allows_manual_load_without_fake_kw(self):
        graph = self._base_graph()
        graph = add_radial_circuit(
            graph,
            circuit_id="C-MAN",
            description="Known outlet",
            load_kw=None,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        exact = CircuitDesignRequest(
            circuit_id="C-MAN",
            description="Known outlet",
            load_type="a",
            load_value=32.0,
            voltage_v=400.0,
            phase="three",
            power_factor=None,
            demand_factor=1.0,
            material="copper",
        )

        hierarchy = calculate_board_hierarchy(graph, (exact,))
        child = hierarchy.plans_by_board_id["DB-02"]
        row = child.schedule_rows[0]
        self.assertEqual(row.load_type, "a")
        self.assertEqual(row.load_value, 32.0)
        self.assertAlmostEqual(row.design_current_a, 32.0)

        root = hierarchy.plans_by_board_id["DB-01"]
        self.assertAlmostEqual(root.phase_balance.l1_current_a, 32.0)
        self.assertAlmostEqual(root.phase_balance.l2_current_a, 32.0)
        self.assertAlmostEqual(root.phase_balance.l3_current_a, 32.0)

    def test_kva_override_remains_kva_inside_nested_board(self):
        graph = self._base_graph()
        graph = add_radial_circuit(
            graph,
            circuit_id="C-KVA",
            description="Declared apparent load",
            load_kw=None,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        exact = CircuitDesignRequest(
            circuit_id="C-KVA",
            description="Declared apparent load",
            load_type="kva",
            load_value=20.0,
            voltage_v=400.0,
            phase="three",
            power_factor=None,
            demand_factor=0.8,
            material="copper",
        )
        hierarchy = calculate_board_hierarchy(graph, (exact,))
        row = hierarchy.plans_by_board_id["DB-02"].schedule_rows[0]
        self.assertEqual(row.load_type, "kva")
        self.assertEqual(row.load_value, 20.0)
        self.assertEqual(row.demand_factor, 0.8)

    def test_boundary_rejects_unknown_duplicate_and_wrong_voltage_overrides(self):
        graph = self._base_graph()
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Load",
            load_kw=5.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        unknown = CircuitDesignRequest(
            circuit_id="C-99",
            description="Unknown",
            load_type="a",
            load_value=10.0,
            voltage_v=400.0,
            phase="three",
            power_factor=None,
        )
        with self.assertRaisesRegex(ValueError, "unknown graph load"):
            calculation_boundaries_from_graph(graph, (unknown,))

        valid = CircuitDesignRequest(
            circuit_id="C-01",
            description="Load",
            load_type="a",
            load_value=10.0,
            voltage_v=400.0,
            phase="three",
            power_factor=None,
        )
        with self.assertRaisesRegex(ValueError, "duplicate circuit request override"):
            calculation_boundaries_from_graph(graph, (valid, valid))

        wrong_voltage = CircuitDesignRequest(
            circuit_id="C-01",
            description="Load",
            load_type="a",
            load_value=10.0,
            voltage_v=415.0,
            phase="three",
            power_factor=None,
        )
        with self.assertRaisesRegex(ValueError, "does not match board line-to-line voltage"):
            calculation_boundaries_from_graph(graph, (wrong_voltage,))

    def test_boundary_requires_override_when_graph_has_no_kw_basis(self):
        graph = self._base_graph()
        graph = add_radial_circuit(
            graph,
            circuit_id="C-MAN",
            description="Known outlet",
            load_kw=None,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        with self.assertRaisesRegex(ValueError, "provide an exact circuit request override"):
            calculation_boundaries_from_graph(graph)


if __name__ == "__main__":
    unittest.main()
