import unittest

from src.board_graph import (
    add_field_feeder,
    add_radial_circuit,
    add_sub_board_feeder,
    board_plan_request_from_graph,
    make_radial_board_graph,
)
from src.board_planner import calculate_board_plan
from src.field_rollup import calculate_field_rollups, enrich_graph_with_field_rollups


class FieldRollupTests(unittest.TestCase):
    def _two_phase_field(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-LTG",
            field_id="LTG",
            description="Lighting field",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-01",
            description="Zone A",
            load_kw=2.3,
            phase="single",
            power_factor=1.0,
            phase_preference="L1",
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="LTG-02",
            description="Zone B",
            load_kw=2.3,
            phase="single",
            power_factor=1.0,
            phase_preference="L2",
            parent_busbar_id="F-LTG:LTG:busbar",
        )
        plan = calculate_board_plan(board_plan_request_from_graph(graph))
        return graph, plan

    def test_field_rollup_uses_allocated_child_phase_currents(self):
        graph, plan = self._two_phase_field()
        rollup = calculate_field_rollups(graph, plan, {"LTG": "copper"})[0]

        self.assertEqual(rollup.status, "PROVISIONAL")
        self.assertEqual(rollup.descendant_circuit_ids, ("LTG-01", "LTG-02"))
        self.assertAlmostEqual(rollup.phase_demand.l1_current_a, 10.0, places=6)
        self.assertAlmostEqual(rollup.phase_demand.l2_current_a, 10.0, places=6)
        self.assertAlmostEqual(rollup.phase_demand.l3_current_a, 0.0, places=6)
        self.assertAlmostEqual(rollup.required_current_a, 10.0, places=6)
        self.assertEqual(rollup.feeder_design.request.load_type, "a")
        self.assertEqual(rollup.feeder_design.request.phase, "three")
        self.assertEqual(rollup.feeder_design.breaker_a, 10.0)
        self.assertTrue(rollup.contains_single_phase_loads)

    def test_field_feeder_is_not_added_as_an_extra_board_load(self):
        graph, plan = self._two_phase_field()
        calculate_field_rollups(graph, plan, {"LTG": "copper"})

        self.assertEqual(plan.circuit_count, 2)
        self.assertAlmostEqual(plan.phase_balance.l1_current_a, 10.0, places=6)
        self.assertAlmostEqual(plan.phase_balance.l2_current_a, 10.0, places=6)
        self.assertAlmostEqual(plan.phase_balance.l3_current_a, 0.0, places=6)

    def test_rollup_requires_explicit_feeder_material(self):
        graph, plan = self._two_phase_field()
        with self.assertRaisesRegex(ValueError, "explicit feeder conductor material"):
            calculate_field_rollups(graph, plan, {})

    def test_rollup_enriches_existing_field_feeder_nodes(self):
        graph, plan = self._two_phase_field()
        rollups = calculate_field_rollups(graph, plan, {"LTG": "copper"})
        enriched = enrich_graph_with_field_rollups(graph, rollups)

        self.assertEqual(enriched.node_by_id["F-LTG:device"].rating_a, 10.0)
        self.assertIsNotNone(enriched.node_by_id["F-LTG:cable"].cable_mm2)
        self.assertEqual(enriched.node_by_id["F-LTG:LTG:field"].scope_status, "PARTIAL_SCOPE")
        self.assertIn("2 circuits", enriched.node_by_id["F-LTG:LTG:field"].display_detail)
        self.assertIn("FIELD_FEEDER_PROVISIONAL", enriched.node_by_id["F-LTG:device"].issue_codes)

    def test_field_does_not_flatten_a_downstream_sub_board(self):
        graph = add_field_feeder(
            make_radial_board_graph(board_id="DB-01", description="Board"),
            feeder_id="F-01",
            field_id="SERV",
            description="Services",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-DIRECT",
            description="Direct child",
            load_kw=2.3,
            phase="single",
            power_factor=1.0,
            phase_preference="L1",
            parent_busbar_id="F-01:SERV:busbar",
        )
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Child board",
            parent_busbar_id="F-01:SERV:busbar",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-DOWN",
            description="Downstream load",
            load_kw=8.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        plan = calculate_board_plan(board_plan_request_from_graph(graph))
        rollup = calculate_field_rollups(graph, plan, {"SERV": "copper"})[0]

        self.assertEqual(rollup.descendant_circuit_ids, ("C-DIRECT",))
        self.assertAlmostEqual(rollup.required_current_a, 10.0, places=6)


if __name__ == "__main__":
    unittest.main()
