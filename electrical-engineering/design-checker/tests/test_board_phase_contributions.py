import unittest

from src.board_planner import (
    BoardPhaseContribution,
    BoardPlanRequest,
    calculate_board_plan,
)
from src.circuit_engine import CircuitDesignRequest


class BoardPhaseContributionTests(unittest.TestCase):
    def _single_phase(self, circuit_id, load_kw=2.0):
        return CircuitDesignRequest(
            circuit_id=circuit_id,
            description=circuit_id,
            load_type="kw",
            load_value=load_kw,
            voltage_v=230,
            phase="single",
            power_factor=1.0,
            material="copper",
        )

    def test_downstream_phase_vector_is_preserved(self):
        contribution = BoardPhaseContribution(
            contribution_id="DBF-01",
            l1_current_a=42.0,
            l2_current_a=31.0,
            l3_current_a=27.0,
            basis="Calculated child board",
        )
        result = calculate_board_plan(BoardPlanRequest(
            board_id="DB-01",
            description="Parent board",
            circuits=tuple(),
            phase_contributions=(contribution,),
        ))
        self.assertEqual(result.phase_balance.l1_current_a, 42.0)
        self.assertEqual(result.phase_balance.l2_current_a, 31.0)
        self.assertEqual(result.phase_balance.l3_current_a, 27.0)
        self.assertEqual(result.phase_balance.spread_a, 15.0)
        self.assertEqual(result.circuit_count, 0)
        self.assertEqual(result.schedule_rows, tuple())
        self.assertEqual(result.scope_status, "PARTIAL_SCOPE")
        self.assertEqual(result.incomer_candidate.required_current_a, 42.0)

    def test_auto_phase_balancing_uses_downstream_vector_as_existing_load(self):
        contribution = BoardPhaseContribution(
            contribution_id="DBF-01",
            l1_current_a=20.0,
            l2_current_a=5.0,
            l3_current_a=10.0,
            basis="Calculated child board",
        )
        result = calculate_board_plan(BoardPlanRequest(
            board_id="DB-01",
            description="Parent board",
            circuits=(self._single_phase("C-01", load_kw=2.3),),
            phase_contributions=(contribution,),
        ))
        allocation = result.phase_balance.allocations[0]
        self.assertEqual(allocation.assigned_phase, "L2")
        self.assertAlmostEqual(result.phase_balance.l1_current_a, 20.0)
        self.assertGreater(result.phase_balance.l2_current_a, 5.0)
        self.assertAlmostEqual(result.phase_balance.l3_current_a, 10.0)

    def test_invalid_contributions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "basis is required"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-01",
                description="Parent board",
                circuits=tuple(),
                phase_contributions=(BoardPhaseContribution("DBF-01", 1, 2, 3, ""),),
            ))
        with self.assertRaisesRegex(ValueError, "duplicate phase contribution"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-01",
                description="Parent board",
                circuits=tuple(),
                phase_contributions=(
                    BoardPhaseContribution("DBF-01", 1, 2, 3, "A"),
                    BoardPhaseContribution("DBF-01", 2, 3, 4, "B"),
                ),
            ))
        with self.assertRaisesRegex(ValueError, "must contain a current greater than 0"):
            calculate_board_plan(BoardPlanRequest(
                board_id="DB-01",
                description="Parent board",
                circuits=tuple(),
                phase_contributions=(BoardPhaseContribution("DBF-01", 0, 0, 0, "A"),),
            ))


if __name__ == "__main__":
    unittest.main()
