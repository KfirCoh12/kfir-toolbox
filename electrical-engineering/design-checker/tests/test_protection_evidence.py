import unittest

from src.protection_evidence import (
    CableProtectionEvidence,
    CoordinationEvidence,
    FaultEvidence,
    ProtectiveDeviceEvidence,
    conservative_status_from_evidence,
    evidence_readiness,
)


class ProtectionEvidenceTests(unittest.TestCase):
    def _complete_evidence(self):
        return CoordinationEvidence(
            upstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="UP-DEVICE",
                rating_a=100.0,
                settings_ref="UP settings record",
                breaking_capacity_ka=25.0,
            ),
            downstream_device=ProtectiveDeviceEvidence(
                make="Declared manufacturer",
                model="DOWN-DEVICE",
                rating_a=32.0,
                settings_ref="DOWN settings record",
                breaking_capacity_ka=15.0,
            ),
            fault=FaultEvidence(prospective_fault_current_ka=8.0),
            cable=CableProtectionEvidence(
                cable_ref="CABLE-01",
                constraint_ref="declared cable constraint record",
                rule_basis_ref="traceable rule-basis record",
            ),
            manufacturer_coordination_ref="manufacturer table reference",
        )

    def test_empty_evidence_reports_missing_categories(self):
        readiness = evidence_readiness(CoordinationEvidence())

        self.assertFalse(readiness.protection_ready_for_engineering_check)
        self.assertFalse(readiness.selectivity_ready_for_engineering_check)
        self.assertIn(
            "prospective fault current / fault-loop data at the protected point",
            readiness.missing_protection_evidence,
        )
        self.assertIn(
            "manufacturer selectivity/coordination table or verified time-current evidence",
            readiness.missing_selectivity_evidence,
        )

    def test_complete_declared_inputs_mean_ready_not_verified(self):
        evidence = self._complete_evidence()
        readiness = evidence_readiness(evidence)

        self.assertTrue(readiness.protection_ready_for_engineering_check)
        self.assertTrue(readiness.selectivity_ready_for_engineering_check)

        status = conservative_status_from_evidence(
            evidence,
            protection_check_requested=True,
            selectivity_check_requested=True,
        )
        self.assertEqual(status.protection_status, "INSUFFICIENT DATA")
        self.assertEqual(status.selectivity_status, "INSUFFICIENT DATA")
        self.assertNotEqual(status.protection_status, "VERIFIED")
        self.assertNotEqual(status.selectivity_status, "VERIFIED")
        self.assertIn(
            "engineering protection verification has not been implemented/performed",
            status.missing_evidence,
        )
        self.assertIn(
            "engineering selectivity verification has not been implemented/performed",
            status.missing_evidence,
        )

    def test_fault_loop_reference_can_supply_fault_input_category(self):
        evidence = self._complete_evidence()
        evidence = CoordinationEvidence(
            upstream_device=evidence.upstream_device,
            downstream_device=evidence.downstream_device,
            fault=FaultEvidence(fault_loop_ref="FAULT-STUDY-01"),
            cable=evidence.cable,
            manufacturer_coordination_ref=evidence.manufacturer_coordination_ref,
        )

        self.assertTrue(evidence_readiness(evidence).protection_ready_for_engineering_check)

    def test_invalid_numeric_values_do_not_count_as_evidence(self):
        evidence = CoordinationEvidence(
            downstream_device=ProtectiveDeviceEvidence(
                make="M",
                model="D",
                rating_a=32.0,
                breaking_capacity_ka=0.0,
            ),
            fault=FaultEvidence(prospective_fault_current_ka=-1.0),
        )
        readiness = evidence_readiness(evidence)

        self.assertIn(
            "prospective fault current / fault-loop data at the protected point",
            readiness.missing_protection_evidence,
        )
        self.assertIn(
            "downstream breaker breaking capacity",
            readiness.missing_protection_evidence,
        )

    def test_unrequested_checks_remain_not_checked_even_with_evidence(self):
        status = conservative_status_from_evidence(self._complete_evidence())

        self.assertEqual(status.protection_status, "NOT CHECKED")
        self.assertEqual(status.selectivity_status, "NOT CHECKED")
        self.assertEqual(status.missing_evidence, ())


if __name__ == "__main__":
    unittest.main()
