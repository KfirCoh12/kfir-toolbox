import unittest

from src.board_planner import BoardPlanRequest, calculate_board_plan
from src.circuit_engine import CircuitDesignRequest
from src.single_line import build_single_line_diagram


class SingleLineDiagramTests(unittest.TestCase):
    def _circuit(self, circuit_id, description, *, phase="three", load_kw=10):
        return CircuitDesignRequest(
            circuit_id=circuit_id,
            description=description,
            load_type="kw",
            load_value=load_kw,
            voltage_v=400 if phase == "three" else 230,
            phase=phase,
            power_factor=0.9,
            material="copper",
        )

    def test_sld_builds_shared_source_incomer_busbar_and_branch_hierarchy(self):
        plan = calculate_board_plan(BoardPlanRequest(
            board_id="DB-01",
            description="Office board",
            circuits=(
                self._circuit("C-01", "AHU", phase="three", load_kw=18),
                self._circuit("C-02", "Sockets", phase="single", load_kw=3),
            ),
        ))
        sld = build_single_line_diagram(plan)
        self.assertEqual(sld.board_id, "DB-01")
        self.assertEqual(sld.outgoing_count, 2)
        self.assertEqual(len(sld.nodes), 3 + 3 * 2)
        self.assertEqual(len(sld.node_ids), len(set(sld.node_ids)))

        by_id = {node.node_id: node for node in sld.nodes}
        self.assertIsNone(by_id["DB-01:source"].parent_id)
        self.assertEqual(by_id["DB-01:incomer"].parent_id, "DB-01:source")
        self.assertEqual(by_id["DB-01:busbar"].parent_id, "DB-01:incomer")
        self.assertEqual(by_id["DB-01:C-01:device"].parent_id, "DB-01:busbar")
        self.assertEqual(by_id["DB-01:C-01:cable"].parent_id, "DB-01:C-01:device")
        self.assertEqual(by_id["DB-01:C-01:load"].parent_id, "DB-01:C-01:cable")

    def test_sld_preserves_phase_and_calculated_branch_values(self):
        plan = calculate_board_plan(BoardPlanRequest(
            board_id="DB-02",
            description="Three phase board",
            circuits=(self._circuit("C-01", "AHU", phase="three", load_kw=18),),
        ))
        sld = build_single_line_diagram(plan)
        by_id = {node.node_id: node for node in sld.nodes}
        row = plan.schedule_rows[0]
        device = by_id["DB-02:C-01:device"]
        cable = by_id["DB-02:C-01:cable"]
        self.assertEqual(device.phase, "3P")
        self.assertEqual(device.rating_a, row.breaker_a)
        self.assertEqual(cable.cable_mm2, row.cable_mm2)
        self.assertEqual(cable.cable_runs, row.cable_runs)
        self.assertEqual(by_id["DB-02:C-01:load"].label, "AHU")

    def test_sld_keeps_unverified_single_phase_cable_explicit(self):
        plan = calculate_board_plan(BoardPlanRequest(
            board_id="DB-03",
            description="Single phase scope board",
            circuits=(self._circuit("C-01", "Sockets", phase="single", load_kw=3),),
        ))
        sld = build_single_line_diagram(plan)
        by_id = {node.node_id: node for node in sld.nodes}
        cable = by_id["DB-03:C-01:cable"]
        self.assertEqual(cable.label, "Cable sizing not verified")
        self.assertIsNone(cable.cable_mm2)
        self.assertEqual(cable.scope_status, "PARTIAL_SCOPE")
        self.assertIn("cable_dataset_phase_unsupported", cable.issue_codes)

    def test_sld_does_not_claim_incomer_or_busbar_verification(self):
        plan = calculate_board_plan(BoardPlanRequest(
            board_id="DB-04",
            description="Scope board",
            circuits=(self._circuit("C-01", "AHU", phase="three", load_kw=18),),
        ))
        sld = build_single_line_diagram(plan)
        by_id = {node.node_id: node for node in sld.nodes}
        self.assertEqual(by_id["DB-04:incomer"].scope_status, "PARTIAL_SCOPE")
        self.assertIn(
            "board_incomer_protection_not_verified",
            by_id["DB-04:incomer"].issue_codes,
        )
        self.assertEqual(by_id["DB-04:busbar"].scope_status, "PARTIAL_SCOPE")
        self.assertIn(
            "board_busbar_rating_not_selected",
            by_id["DB-04:busbar"].issue_codes,
        )


if __name__ == "__main__":
    unittest.main()
