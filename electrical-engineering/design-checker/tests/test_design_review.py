import unittest

from src.design_review import design_review_summary
from src.sample_boards import office_700m2_150_people_board
from src.working_board_plan import calculate_working_board


class DesignReviewTests(unittest.TestCase):
    def test_office_fixture_resolves_final_circuit_cable_attention(self):
        calculated = calculate_working_board(office_700m2_150_people_board())
        summary = design_review_summary(calculated)

        # The 27 single-phase final circuits now receive source-backed Method E
        # two-loaded-conductor cable candidates. The remaining review records are
        # field-level limitations around mixed single-phase feeder neutral/harmonics.
        self.assertEqual(summary.attention_count, 0)
        self.assertEqual(summary.limitation_count, 3)
        self.assertEqual(len(summary.issues), 3)
        self.assertNotIn("GP-01", summary.issues_by_target)
        self.assertNotIn("AV-03", summary.issues_by_target)
        self.assertNotIn("HVAC-01", summary.issues_by_target)

    def test_remaining_office_review_groups_only_field_scope_limitations(self):
        summary = design_review_summary(
            calculate_working_board(office_700m2_150_people_board())
        )
        self.assertEqual(len(summary.groups), 1)

        field_scope = summary.groups[0]
        self.assertEqual(field_scope.code, "FIELD_FEEDER_MIXED_SINGLE_PHASE_SCOPE")
        self.assertEqual(field_scope.severity, "LIMITATION")
        self.assertEqual(field_scope.scope, "FIELD_FEEDER")
        self.assertEqual(field_scope.target_count, 3)
        self.assertEqual(len(field_scope.target_ids), 3)
        self.assertIn("F-GP", field_scope.target_ids)

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
