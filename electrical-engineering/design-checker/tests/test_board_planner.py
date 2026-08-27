import unittest

from src.board_planner import BoardPlanRequest, calculate_board_plan
from src.circuit_engine import CircuitDesignRequest


class BoardPlannerTests(unittest.TestCase):
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
        self.assertFalse(r.board_level_checks_implemented)

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
