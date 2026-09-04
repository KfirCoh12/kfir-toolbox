import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HMI = (ROOT / "src" / "board_planner_hmi.py").read_text(encoding="utf-8")


class PlannerProposalUITests(unittest.TestCase):
    def test_pending_proposals_have_explicit_apply_and_reject_actions(self):
        self.assertIn("Proposed board changes", HMI)
        self.assertIn("Apply proposal", HMI)
        self.assertIn("Reject", HMI)
        self.assertIn("pending_board_proposals", HMI)

    def test_proposal_preview_uses_backend_recalculation(self):
        self.assertIn("preview_board_proposal", HMI)
        self.assertIn("Preview recalculated successfully through the existing Planner engine.", HMI)
        self.assertIn("Attention after", HMI)
        self.assertIn("Limitations after", HMI)

    def test_stale_revision_disables_apply(self):
        self.assertIn('proposal.get("base_revision", -1)', HMI)
        self.assertIn('state["revision"]', HMI)
        self.assertIn("disabled=stale", HMI)

    def test_project_state_is_part_of_hmi_refresh_fingerprint(self):
        self.assertIn('"project_state": project_state_from_payload(board)', HMI)
        self.assertIn("REV {project_revision}", HMI)


if __name__ == "__main__":
    unittest.main()
