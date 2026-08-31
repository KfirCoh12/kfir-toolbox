"""Deterministic verifier for one narrow declared breaking-capacity relationship.

The verifier checks only whether the declared downstream device breaking capacity is
not less than the declared prospective fault current at the protected point. This is a
numeric engineering check with explicit provenance; it is not a claim of IEC
compliance, overall device suitability, fault-protection compliance, selectivity,
backup protection, or correct manufacturer application.
"""
from math import isfinite

from .protection_evidence import CoordinationEvidence
from .protection_verification import (
    EvidenceSource,
    ProtectionVerificationResult,
    VerificationProvenance,
    VerifierIdentity,
    make_not_verified_result,
    make_unverified_result,
    make_verified_result,
)

VERIFIER = VerifierIdentity(name="declared-breaking-capacity-comparator", version="1.0")


def _positive(value: float | None) -> bool:
    return value is not None and isfinite(value) and value > 0


def verify_breaking_capacity(
    *,
    upstream_node_id: str,
    downstream_node_id: str,
    evidence: CoordinationEvidence,
    requested: bool = True,
    rule_basis_ref: str | None = None,
    evidence_record_ref: str | None = None,
) -> ProtectionVerificationResult:
    """Compare declared breaking capacity against declared prospective fault current.

    A decisive verdict requires both numeric inputs plus caller-supplied traceability
    references. The comparison implemented is only:

        declared downstream breaking capacity >= declared prospective fault current

    The caller remains responsible for ensuring the declared quantities and rule basis
    are applicable to the actual device/system conditions.
    """
    if not requested:
        return make_unverified_result(
            check="BREAKING_CAPACITY",
            requested=False,
            basis="Breaking-capacity comparison was not requested.",
        )

    fault_ka = (
        evidence.fault.prospective_fault_current_ka
        if evidence.fault is not None
        else None
    )
    capacity_ka = (
        evidence.downstream_device.breaking_capacity_ka
        if evidence.downstream_device is not None
        else None
    )

    missing: list[str] = []
    if not _positive(fault_ka):
        missing.append("positive prospective fault current at the protected point")
    if not _positive(capacity_ka):
        missing.append("positive downstream device breaking capacity")
    if rule_basis_ref is None or not rule_basis_ref.strip():
        missing.append("traceable breaking-capacity rule basis reference")
    if evidence_record_ref is None or not evidence_record_ref.strip():
        missing.append("traceable evidence record reference for declared numeric inputs")

    if missing:
        return make_unverified_result(
            check="BREAKING_CAPACITY",
            requested=True,
            missing_evidence=tuple(missing),
            basis=(
                "No breaking-capacity verdict was produced because the narrow numeric "
                "comparison lacks required declared inputs or traceability."
            ),
        )

    provenance = VerificationProvenance(
        upstream_node_id=upstream_node_id,
        downstream_node_id=downstream_node_id,
        verifier=VERIFIER,
        evidence_sources=(
            EvidenceSource(
                kind="ENGINEERING_RECORD",
                reference=evidence_record_ref,
                description=(
                    "Declared prospective fault current and downstream device breaking capacity"
                ),
            ),
        ),
        rule_basis_ref=rule_basis_ref,
    )

    assert fault_ka is not None
    assert capacity_ka is not None
    basis = (
        f"Declared downstream breaking capacity {capacity_ka:g} kA compared with declared "
        f"prospective fault current {fault_ka:g} kA using rule basis {rule_basis_ref}. "
        "This verdict covers only that declared numeric comparison."
    )

    if capacity_ka >= fault_ka:
        return make_verified_result(
            check="BREAKING_CAPACITY",
            provenance=provenance,
            basis=basis,
        )
    return make_not_verified_result(
        check="BREAKING_CAPACITY",
        provenance=provenance,
        basis=basis,
    )
