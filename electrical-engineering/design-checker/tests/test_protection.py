import unittest

from src.protection import (
    build_protection_plan,
    coordination_status,
    load_sized_breaker_candidate,
)


class ProtectionPlanningTests(unittest.TestCase):
    def test_load_sizing_candidate_is_separate_from_verification(self):
        plan = build_protection_plan(design_current_a=27.5)
        self.assertEqual(plan.candidate.status, "CANDIDATE")
        self.assertEqual(plan.candidate.breaker_rating_a, 32.0)
        self.assertEqual(plan.coordination.protection_status, "NOT CHECKED")
        self.assertEqual(plan.coordination.selectivity_status, "NOT CHECKED")
        self.assertIn("load-sized candidate only", plan.candidate.basis.lower())

    def test_requested_protection_check_stays_insufficient_without_evidence(self):
        status = coordination_status(protection_check_requested=True)
        self.assertEqual(status.protection_status, "INSUFFICIENT DATA")
        self.assertEqual(status.selectivity_status, "NOT CHECKED")
        self.assertIn("fault", " ".join(status.missing_evidence).lower())
        self.assertNotEqual(status.protection_status, "VERIFIED")

    def test_requested_selectivity_check_stays_insufficient_without_manufacturer_evidence(self):
        status = coordination_status(selectivity_check_requested=True)
        self.assertEqual(status.protection_status, "NOT CHECKED")
        self.assertEqual(status.selectivity_status, "INSUFFICIENT DATA")
        evidence = " ".join(status.missing_evidence).lower()
        self.assertIn("make/model", evidence)
        self.assertIn("manufacturer", evidence)
        self.assertNotEqual(status.selectivity_status, "VERIFIED")

    def test_requesting_both_checks_never_promotes_candidate_to_verified(self):
        plan = build_protection_plan(
            design_current_a=63.1,
            protection_check_requested=True,
            selectivity_check_requested=True,
        )
        self.assertEqual(plan.candidate.breaker_rating_a, 80.0)
        self.assertEqual(plan.coordination.protection_status, "INSUFFICIENT DATA")
        self.assertEqual(plan.coordination.selectivity_status, "INSUFFICIENT DATA")
        self.assertIn("traceable evidence", plan.coordination.basis.lower())

    def test_catalog_exhaustion_does_not_invent_breaker_rating(self):
        candidate = load_sized_breaker_candidate(design_current_a=700.0)
        self.assertEqual(candidate.status, "NO_CANDIDATE")
        self.assertIsNone(candidate.breaker_rating_a)

    def test_invalid_design_current_is_rejected(self):
        for value in (0.0, -1.0, float("inf"), float("nan")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    load_sized_breaker_candidate(design_current_a=value)

    def test_custom_breaker_catalog_must_be_ordered_and_positive(self):
        with self.assertRaisesRegex(ValueError, "ascending"):
            load_sized_breaker_candidate(
                design_current_a=10.0,
                breaker_ratings_a=(16, 10, 20),
            )
        with self.assertRaisesRegex(ValueError, "greater than 0"):
            load_sized_breaker_candidate(
                design_current_a=10.0,
                breaker_ratings_a=(0, 16, 20),
            )


if __name__ == "__main__":
    unittest.main()
