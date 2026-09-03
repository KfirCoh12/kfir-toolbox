import unittest

from src.design_review import design_review_summary
from src.sample_boards import office_700m2_150_people_board
from src.working_board_plan import calculate_working_board


class DesignReviewTests(unittest.TestCase):
    def test_office_fixture_turns_current_unresolved_scope_into_targeted_issues(self):
        calculated = calculate_working_board(office_700m2_150_people_board())
        summary = design_review_summary(calculated)

        # The fixture has 27 single-phase final circuits. Their design currents and
        # breaker candidates are calculated, while automatic cable selection remains
        # outside the current single-phase dataset.
        self.assertEqual(summary.attention_count, 27)
        self.assertEqual(summary.limitation_count, 3)
        self.assertEqual(len(summary.issues), 30)

        gp01 = summary.issues_by_target["GP-01"]
        self.assertEqual(len(gp01), 1)
        self.assertEqual(gp01[0].code, "SINGLE_PHASE_CABLE_SCOPE")
        self.assertEqual(gp01[0].severity, "ATTENTION")
        self.assertEqual(gp01[0].route_circuit_id, "GP-01")

        self.assertNotIn("HVAC-01", summary.issues_by_target)

    def test_mixed_single_phase_field_is_limitation_not_failure(self):
        calculated = calculate_working_board(office_700m2_150_people_board())
        summary = design_review_summary(calculated)
        field_issue = summary.issues_by_target["F-GP"]
        matching = [
            issue
            for issue in field_issue
            if issue.code == "FIELD_FEEDER_MIXED_SINGLE_PHASE_SCOPE"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].severity, "LIMITATION")
        self.assertIn("not verified", matching[0].detail)

    def test_sub_board_without_installation_declaration_gets_actionable_feeder_issue(self):
        payload = {
            "board_id": "MAIN-DB",
            "description": "Main board",
            "line_to_line_voltage_v": 400.0,
            "line_to_neutral_voltage_v": 230.0,
            "branches": [
                {
                    "uid": "b1",
                    "kind": "sub_board",
                    "parent_key": "root",
                    "feeder_id": "SB-01",
                    "sub_board_id": "DB-02",
                    "description": "Downstream board",
                    "material": "copper",
                },
                {
                    "uid": "b2",
                    "kind": "final",
                    "parent_key": "b1",
                    "circuit_id": "C-01",
                    "description": "Three-phase load",
                    "mode": "auto",
                    "load_kw": 20.0,
                    "phase": "three",
                    "power_factor": 0.9,
                    "demand_factor": 1.0,
                    "material": "copper",
                    "phase_preference": "Auto",
                    "connection_option_id": None,
                },
            ],
            "uid_counter": 2,
        }
        summary = design_review_summary(calculate_working_board(payload))
        issues = summary.issues_by_target["SB-01"]
        self.assertTrue(
            any(issue.code == "SUB_BOARD_FEEDER_CABLE_NOT_DECLARED" for issue in issues)
        )
        self.assertTrue(all(issue.severity == "ATTENTION" for issue in issues))
        self.assertTrue(all(issue.route_circuit_id == "SB-01" for issue in issues))

    def test_review_model_never_creates_protection_or_selectivity_verdicts(self):
        summary = design_review_summary(
            calculate_working_board(office_700m2_150_people_board())
        )
        combined = " ".join(
            f"{issue.code} {issue.title} {issue.detail}" for issue in summary.issues
        ).lower()
        self.assertNotIn("selectivity", combined)
        self.assertNotIn("protection verified", combined)
        self.assertNotIn("compliant", combined)
        self.assertNotIn("failed", combined)


if __name__ == "__main__":
    unittest.main()
