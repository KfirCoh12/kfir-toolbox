import unittest

from src.sample_boards import office_700m2_150_people_board
from src.working_board_plan import calculate_working_board


class SampleBoardTests(unittest.TestCase):
    def test_office_fixture_has_realistic_scale_and_structure(self):
        board = office_700m2_150_people_board()
        branches = board["branches"]
        finals = [branch for branch in branches if branch["kind"] == "final"]
        fields = [branch for branch in branches if branch["kind"] == "field"]

        self.assertEqual(board["declared_main_incomer_a"], 400.0)
        self.assertEqual(board["scenario_area_m2"], 700.0)
        self.assertEqual(board["scenario_people"], 150)
        self.assertEqual(len(fields), 5)
        self.assertEqual(len(finals), 40)
        self.assertTrue(any(branch["phase"] == "single" for branch in finals))
        self.assertTrue(any(branch["phase"] == "three" for branch in finals))

    def test_office_fixture_runs_through_working_board_calculation(self):
        result = calculate_working_board(office_700m2_150_people_board())

        # Working-board contexts include the five field feeders plus 40 finals.
        self.assertEqual(len(result.circuit_contexts), 45)
        self.assertGreater(result.hierarchy.root.plan.phase_balance.max_phase_current_a, 300.0)
        self.assertLessEqual(result.hierarchy.root.plan.phase_balance.max_phase_current_a, 400.0)
        self.assertEqual(result.hierarchy.root.plan.incomer_candidate.breaker_rating_a, 400.0)


if __name__ == "__main__":
    unittest.main()
