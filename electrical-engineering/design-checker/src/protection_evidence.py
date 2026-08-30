"""Structured evidence inputs for future protection/selectivity verification.

This module records traceable engineering inputs without interpreting them as an IEC,
manufacturer, or selectivity verdict. Presence of evidence is not proof that a check
passes; it only allows callers to distinguish missing inputs from supplied inputs.
"""
from dataclasses import dataclass
from math import isfinite

from .protection import ProtectionCoordinationStatus, VerificationStatus


@dataclass(frozen=True)
class ProtectiveDeviceEvidence:
    """Declared identity/settings for one protective device."""

    make: str | None = None
    model: str | None = None
    rating_a: float | None = None
    settings_ref: str | None = None
    breaking_capacity_ka: float | None = None


@dataclass(frozen=True)
class FaultEvidence:
    """Declared fault information at the protected point."""

    prospective_fault_current_ka: float | None = None
    fault_loop_ref: str | None = None


@dataclass(frozen=True)
class CableProtectionEvidence:
    """Traceable cable-protection input references, without rule evaluation."""

    cable_ref: str | None = None
    constraint_ref: str | None = None
    rule_basis_ref: str | None = None


@dataclass(frozen=True)
class CoordinationEvidence:
    """Evidence bundle for one upstream/downstream protective-device pair."""

    upstream_device: ProtectiveDeviceEvidence | None = None
    downstream_device: ProtectiveDeviceEvidence | None = None
    fault: FaultEvidence | None = None
    cable: CableProtectionEvidence | None = None
    manufacturer_coordination_ref: str | None = None
    time_current_evidence_ref: str | None = None


@dataclass(frozen=True)
class EvidenceReadiness:
    """Input-readiness result only; never a verification verdict."""

    protection_ready_for_engineering_check: bool
    selectivity_ready_for_engineering_check: bool
    missing_protection_evidence: tuple[str, ...]
    missing_selectivity_evidence: tuple[str, ...]
    basis: str


def _text_present(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _positive_number_present(value: float | None) -> bool:
    return value is not None and isfinite(value) and value > 0


def _device_identity_complete(device: ProtectiveDeviceEvidence | None) -> bool:
    return (
        device is not None
        and _text_present(device.make)
        and _text_present(device.model)
        and _positive_number_present(device.rating_a)
    )


def evidence_readiness(evidence: CoordinationEvidence) -> EvidenceReadiness:
    """Report whether minimum declared inputs exist for later engineering checks.

    ``ready`` means only that the expected input categories have been supplied. This
    function performs no curve comparison, fault calculation, breaking-capacity
    comparison, cable rule check, or manufacturer-table interpretation.
    """
    missing_protection: list[str] = []
    missing_selectivity: list[str] = []

    if not _positive_number_present(
        evidence.fault.prospective_fault_current_ka if evidence.fault else None
    ) and not _text_present(evidence.fault.fault_loop_ref if evidence.fault else None):
        missing_protection.append("prospective fault current / fault-loop data at the protected point")

    downstream = evidence.downstream_device
    if not _device_identity_complete(downstream):
        missing_protection.append("downstream breaker make/model/rating")
    if not _positive_number_present(downstream.breaking_capacity_ka if downstream else None):
        missing_protection.append("downstream breaker breaking capacity")

    cable = evidence.cable
    if not (
        cable is not None
        and _text_present(cable.cable_ref)
        and _text_present(cable.constraint_ref)
        and _text_present(cable.rule_basis_ref)
    ):
        missing_protection.append("cable protective constraints and verified rule basis")

    if not _device_identity_complete(evidence.upstream_device) or not _device_identity_complete(
        evidence.downstream_device
    ):
        missing_selectivity.append("upstream and downstream protective-device make/model/rating")

    if not (
        _text_present(evidence.manufacturer_coordination_ref)
        or _text_present(evidence.time_current_evidence_ref)
    ):
        missing_selectivity.append(
            "manufacturer selectivity/coordination table or verified time-current evidence"
        )

    return EvidenceReadiness(
        protection_ready_for_engineering_check=not missing_protection,
        selectivity_ready_for_engineering_check=not missing_selectivity,
        missing_protection_evidence=tuple(missing_protection),
        missing_selectivity_evidence=tuple(missing_selectivity),
        basis=(
            "Readiness confirms only that declared evidence categories are present. "
            "It does not verify protection, selectivity, standards compliance, or manufacturer claims."
        ),
    )


def conservative_status_from_evidence(
    evidence: CoordinationEvidence,
    *,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
) -> ProtectionCoordinationStatus:
    """Expose evidence-aware missing inputs without ever self-promoting to VERIFIED.

    Even a complete evidence bundle remains ``INSUFFICIENT DATA`` here because this
    module deliberately contains no engineering verification engine. A future verifier
    must explicitly consume and validate the evidence before returning ``VERIFIED``.
    """
    readiness = evidence_readiness(evidence)
    protection_status: VerificationStatus = (
        "INSUFFICIENT DATA" if protection_check_requested else "NOT CHECKED"
    )
    selectivity_status: VerificationStatus = (
        "INSUFFICIENT DATA" if selectivity_check_requested else "NOT CHECKED"
    )

    missing: list[str] = []
    if protection_check_requested:
        missing.extend(readiness.missing_protection_evidence)
    if selectivity_check_requested:
        missing.extend(readiness.missing_selectivity_evidence)

    if protection_check_requested and readiness.protection_ready_for_engineering_check:
        missing.append("engineering protection verification has not been implemented/performed")
    if selectivity_check_requested and readiness.selectivity_ready_for_engineering_check:
        missing.append("engineering selectivity verification has not been implemented/performed")

    return ProtectionCoordinationStatus(
        protection_status=protection_status,
        selectivity_status=selectivity_status,
        missing_evidence=tuple(dict.fromkeys(missing)),
        basis=(
            "Evidence presence is tracked separately from engineering verification. "
            "No status is promoted to VERIFIED by this evidence model."
        ),
    )
