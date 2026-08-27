import unittest

from src.board_planner import (
    BoardPhasePreference,
    BoardPlanRequest,
    calculate_board_plan,
)
from src.circuit_engine import CircuitDesignRequest


class BoardPlannerTests(unittest.TestCase):
    def _circuit(self, circuit_id, description, *, phase="three", load_kw=10, voltage_v=None):
        return CircuitDesignRequest(
            circuit_id=circuit_id,
            description=description,
            load_type="kw",
            load_value=load_kw,
            voltage_v=voltage_v if voltage_v is not None else (400 if phase == "three" else 230),
            phase=phase,
            power_factor=0.9,
            material="copper",
        )

    def test_board_runs_multiple_consumers_through_shared_circuit_engine(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-01",
            description="Office distribution board",
            circuits=(
                self._circuit("C-01", "Lighting", load_kw=5),
                self._circuit("C-02", "Sockets", load_kw=8),
                self._circuit("C-03", "AHU", load_kw=18),
            ),
        ))
        self.assertEqual(r.circuit_count, 3)
        self.assertEqual(tuple(c.request.circuit_id for c in r.circuits), ("C-01", "C-02", "C-03"))
        self.assertTrue(all(c.breaker_a is not None for c in r.circuits))
        self.assertEqual(r.scope_status, "SUPPORTED_SCOPE")
        self.assertTrue(r.phase_balancing_implemented)
        self.assertTrue(r.incomer_candidate_implemented)
        self.assertFalse(r.board_level_checks_implemented)

    def test_board_exposes_schedule_rows_without_ui_specific_logic(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-01A",
            description="Schedule test board",
            circuits=(
                self._circuit("C-01", "Lighting", load_kw=5),
                self._circuit("C-02", "AHU", load_kw=18),
            ),
        ))
        rows = r.schedule_rows
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].circuit_id, "C-01")
        self.assertEqual(rows[0].description, "Lighting")
        self.assertEqual(rows[0].assigned_phase, "3P")
        self.assertTrue(rows[0].phase_locked)
        self.assertEqual(rows[0].load_type, "kw")
        self.assertEqual(rows[0].load_value, 5)
        self.assertGreater(rows[0].design_current_a, 0)
        self.assertIsNotNone(rows[0].breaker_a)
        self.assertIsNotNone(rows[0].cable_mm2)
        self.assertEqual(rows[0].scope_status, "SUPPORTED_SCOPE")

    def test_schedule_row_exposes_blocking_issue_codes(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-01B",
            description="Single phase scope test",
            circuits=(self._circuit("C-01", "Appliance", phase="single", load_kw=3),),
        ))
        row = r.schedule_rows[0]
        self.assertEqual(row.assigned_phase, "L1")
        self.assertFalse(row.phase_locked)
        self.assertEqual(row.scope_status, "PARTIAL_SCOPE")
        self.assertIn("cable_dataset_phase_unsupported", row.blocking_issue_codes)

    def test_three_phase_circuit_contributes_equally_to_all_phases(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-BAL-01",
            description="Three phase balance test",
            circuits=(self._circuit("C-01", "AHU", phase="three", load_kw=18),),
        ))
        balance = r.phase_balance
        self.assertAlmostEqual(balance.l1_current_a, balance.l2_current_a)
        self.assertAlmostEqual(balance.l2_current_a, balance.l3_current_a)
        self.assertAlmostEqual(balance.spread_a, 0.0)
        self.assertEqual(balance.allocations[0].assigned_phase, "3P")
        self.assertTrue(balance.allocations[0].locked)

    def test_single_phase_circuits_are_balanced_largest_first(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-BAL-02",
            description="Single phase balance test",
            circuits=(
                self._circuit("C-01", "Largest", phase="single", load_kw=6),
                self._circuit("C-02", "Medium", phase="single", load_kw=4),
                self._circuit("C-03", "Small A", phase="single", load_kw=2),
                self._circuit("C-04", "Small B", phase="single", load_kw=2),
            ),
        ))
        assigned = {a.circuit_id: a.assigned_phase for a in r.phase_balance.allocations}
        self.assertEqual(assigned["C-01"], "L1")
        self.assertEqual(assigned["C-02"], "L2")
        self.assertEqual(assigned["C-03"], "L3")
        self.assertEqual(assigned["C-04"], "L3")
        self.assertAlmostEqual(r.phase_balance.l2_current_a, r.phase_balance.l3_current_a)
        self.assertGreater(r.phase_balance.l1_current_a, r.phase_balance.l2_current_a)
        self.assertGreater(r.phase_balance.spread_a, 0.0)

    def test_locked_phase_is_respected_and_unlocked_circuits_balance_around_it(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-BAL-LOCK-01",
            description="Locked phase balance test",
            circuits=(
                self._circuit("C-01", "Locked large", phase="single", load_kw=6),
                self._circuit("C-02", "Auto A", phase="single", load_kw=4),
                self._circuit("C-03", "Auto B", phase="single", load_kw=4),
            ),
            phase_preferences=(BoardPhasePreference("C-01", "L3"),),
        ))
        allocations = {a.circuit_id: a for a in r.phase_balance.allocations}
        self.assertEqual(allocations["C-01"].assigned_phase, "L3")
        self.assertTrue(allocations["C-01"].locked)
        self.assertEqual({allocations["C-02"].assigned_phase, allocations["C-03"].assigned_phase}, {"L1", "L2"})
        self.assertFalse(allocations["C-02"].locked)
        self.assertFalse(allocations["C-03"].locked)
        row = next(row for row in r.schedule_rows if row.circuit_id == "C-01")
        self.assertTrue(row.phase_locked)

    def test_invalid_phase_preferences_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown circuit"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-BAL-LOCK-02",
                description="Unknown preference",
                circuits=(self._circuit("C-01", "Load", phase="single", load_kw=2),),
                phase_preferences=(BoardPhasePreference("C-99", "L1"),),
            ))
        with self.assertRaisesRegex(ValueError, "single-phase circuit"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-BAL-LOCK-03",
                description="Three phase preference",
                circuits=(self._circuit("C-01", "Load", phase="three", load_kw=10),),
                phase_preferences=(BoardPhasePreference("C-01", "L1"),),
            ))
        with self.assertRaisesRegex(ValueError, "duplicate phase preference"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-BAL-LOCK-04",
                description="Duplicate preference",
                circuits=(self._circuit("C-01", "Load", phase="single", load_kw=2),),
                phase_preferences=(
                    BoardPhasePreference("C-01", "L1"),
                    BoardPhasePreference("C-01", "L2"),
                ),
            ))

    def test_mixed_board_balancing_preserves_three_phase_base_load(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-BAL-03",
            description="Mixed balance test",
            circuits=(
                self._circuit("C-01", "Three phase base", phase="three", load_kw=12),
                self._circuit("C-02", "Single phase A", phase="single", load_kw=3),
                self._circuit("C-03", "Single phase B", phase="single", load_kw=3),
                self._circuit("C-04", "Single phase C", phase="single", load_kw=3),
            ),
        ))
        balance = r.phase_balance
        self.assertAlmostEqual(balance.l1_current_a, balance.l2_current_a)
        self.assertAlmostEqual(balance.l2_current_a, balance.l3_current_a)
        self.assertAlmostEqual(balance.spread_a, 0.0)
        assigned = tuple(a.assigned_phase for a in balance.allocations[1:])
        self.assertEqual(set(assigned), {"L1", "L2", "L3"})

    def test_incomer_candidate_uses_highest_planned_phase_current(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-INC-01",
            description="Incomer candidate test",
            circuits=(self._circuit("C-01", "AHU", phase="three", load_kw=18),),
        ))
        candidate = r.incomer_candidate
        self.assertEqual(candidate.status, "CANDIDATE")
        self.assertAlmostEqual(candidate.required_current_a, r.phase_balance.max_phase_current_a)
        self.assertEqual(candidate.breaker_rating_a, 32.0)
        self.assertIn("no additional board-level diversity", candidate.basis.lower())
        self.assertIn("protection verification", candidate.basis.lower())

    def test_incomer_candidate_does_not_invent_rating_above_catalog(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-INC-02",
            description="Incomer catalog exhaustion",
            circuits=tuple(
                self._circuit(f"C-{i:02d}", f"Large load {i}", phase="three", load_kw=100)
                for i in range(1, 5)
            ),
        ))
        self.assertGreater(r.phase_balance.max_phase_current_a, 630)
        self.assertEqual(r.incomer_candidate.status, "NO_CANDIDATE")
        self.assertIsNone(r.incomer_candidate.breaker_rating_a)

    def test_board_supply_voltage_contract_accepts_declared_custom_system(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-SYS-01",
            description="Custom voltage board",
            line_to_line_voltage_v=415,
            line_to_neutral_voltage_v=240,
            circuits=(
                self._circuit("C-01", "Three phase", phase="three", voltage_v=415),
                self._circuit("C-02", "Single phase", phase="single", load_kw=2, voltage_v=240),
            ),
        ))
        self.assertEqual(r.request.line_to_line_voltage_v, 415)
        self.assertEqual(r.request.line_to_neutral_voltage_v, 240)

    def test_board_rejects_circuit_voltage_that_does_not_match_supply_system(self):
        with self.assertRaisesRegex(ValueError, "does not match the board line-to-line voltage"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-SYS-02",
                description="Mismatched board",
                circuits=(self._circuit("C-01", "Wrong voltage", phase="three", voltage_v=415),),
            ))
        with self.assertRaisesRegex(ValueError, "does not match the board line-to-neutral voltage"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-SYS-03",
                description="Mismatched board",
                circuits=(self._circuit("C-01", "Wrong voltage", phase="single", voltage_v=240),),
            ))

    def test_board_rejects_non_positive_or_non_finite_supply_voltage(self):
        with self.assertRaises(ValueError):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-SYS-04",
                description="Bad voltage",
                circuits=(self._circuit("C-01", "Load"),),
                line_to_line_voltage_v=0,
            ))
        with self.assertRaises(ValueError):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-SYS-05",
                description="Bad voltage",
                circuits=(self._circuit("C-01", "Load"),),
                line_to_line_voltage_v=float("nan"),
            ))

    def test_board_exposes_circuits_with_blocking_scope_issues(self):
        r = calculate_board_plan(BoardPlanRequest(
            board_id="DB-02",
            description="Mixed board",
            circuits=(
                self._circuit("C-01", "Three-phase load", phase="three"),
                self._circuit("C-02", "Single-phase load", phase="single", load_kw=3),
            ),
        ))
        self.assertEqual(r.scope_status, "PARTIAL_SCOPE")
        self.assertEqual(r.blocking_circuit_ids, ("C-02",))

    def test_duplicate_circuit_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-03",
                description="Duplicate IDs",
                circuits=(
                    self._circuit("C-01", "Load A"),
                    self._circuit("C-01", "Load B"),
                ),
            ))

    def test_board_requires_identity_description_and_circuits(self):
        with self.assertRaises(ValueError):
            calculate_board_plan(BoardPlanRequest("", "Board", (self._circuit("C-01", "Load"),)))
        with self.assertRaises(ValueError):
            calculate_board_plan(BoardPlanRequest("DB-04", "", (self._circuit("C-01", "Load"),)))
        with self.assertRaises(ValueError):
            calculate_board_plan(BoardPlanRequest("DB-05", "Empty", tuple()))


if __name__ == "__main__":
    unittest.main()
