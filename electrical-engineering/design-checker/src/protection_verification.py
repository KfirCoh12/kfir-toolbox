"""Strict contracts for protection/selectivity verification engines.

A verified or explicitly negative engineering verdict must identify the verifier, the
exact protection pair, and traceable provenance. Planning, topology,
evidence-readiness, or rating order are not verifiers.
"""
from dataclasses import dataclass
from typing import Literal

from .protection import VerificationStatus

VerificationCheck = Literal[
    "BREAKING_CAPACITY",
    "CABLE_PROTECTION",
    "FAULT_PROTECTION",
    "SELECTIVITY",
]
EvidenceSourceKind = Literal[
    "CALCULATION",
    "MANUFACTURER_TABLE",
    "TIME_CURRENT_EVIDENCE",
    "ENGINEERING_RECORD",
]


@dataclass(frozen=True)
class EvidenceSource:
    """One traceable source used by a verification engine."""

    kind: EvidenceSourceKind
    reference: str
    description: str | None = None


@dataclass(frozen=True)
class VerifierIdentity:
    """Identity of the code/data engine responsible for a verdict."""

    name: str
    version: str


@dataclass(frozen=True)
class VerificationProvenance:
    """Traceability required for an engineering verification result."""

    upstream_node_id: str
    downstream_node_id: str
    verifier: VerifierIdentity
    evidence_sources: tuple[EvidenceSource, ...]
    rule_basis_ref: str

    @property
    def pair_key(self) -> tuple[str, str]:
        return (self.upstream_node_id, self.downstream_node_id)


@dataclass(frozen=True)
class ProtectionVerificationResult:
    """Result contract for one explicit engineering check on one protection pair."""

    check: VerificationCheck
    status: VerificationStatus
    provenance: VerificationProvenance | None
    basis: str
    missing_evidence: tuple[str, ...] = ()


def _nonblank(value: str) -> bool:
    return bool(value.strip())


def _validate_decisive_provenance(
    provenance: VerificationProvenance,
    *,
    basis: str,
) -> None:
    if not _nonblank(provenance.upstream_node_id) or not _nonblank(provenance.downstream_node_id):
        raise ValueError("decisive result requires upstream and downstream protection node IDs")
    if provenance.upstream_node_id == provenance.downstream_node_id:
        raise ValueError("decisive result requires two distinct protection nodes")
    if not _nonblank(provenance.verifier.name) or not _nonblank(provenance.verifier.version):
        raise ValueError("decisive result requires verifier name and version")
    if not provenance.evidence_sources:
        raise ValueError("decisive result requires at least one traceable evidence source")
    for source in provenance.evidence_sources:
        if not _nonblank(source.reference):
            raise ValueError("decisive result evidence sources require nonblank references")
    if not _nonblank(provenance.rule_basis_ref):
        raise ValueError("decisive result requires a traceable rule basis reference")
    if not _nonblank(basis):
        raise ValueError("decisive result requires a nonblank engineering basis")


def make_unverified_result(
    *,
    check: VerificationCheck,
    requested: bool,
    missing_evidence: tuple[str, ...] = (),
    basis: str,
) -> ProtectionVerificationResult:
    """Construct a result where no engineering verdict has been established."""
    return ProtectionVerificationResult(
        check=check,
        status="INSUFFICIENT DATA" if requested else "NOT CHECKED",
        provenance=None,
        basis=basis,
        missing_evidence=missing_evidence if requested else (),
    )


def make_verified_result(
    *,
    check: VerificationCheck,
    provenance: VerificationProvenance,
    basis: str,
) -> ProtectionVerificationResult:
    """Construct ``VERIFIED`` after a dedicated verifier establishes a passing result."""
    _validate_decisive_provenance(provenance, basis=basis)
    return ProtectionVerificationResult(
        check=check,
        status="VERIFIED",
        provenance=provenance,
        basis=basis,
        missing_evidence=(),
    )


def make_not_verified_result(
    *,
    check: VerificationCheck,
    provenance: VerificationProvenance,
    basis: str,
) -> ProtectionVerificationResult:
    """Construct an explicit failing verdict with the same traceability as VERIFIED."""
    _validate_decisive_provenance(provenance, basis=basis)
    return ProtectionVerificationResult(
        check=check,
        status="NOT VERIFIED",
        provenance=provenance,
        basis=basis,
        missing_evidence=(),
    )


def assert_result_matches_pair(
    result: ProtectionVerificationResult,
    *,
    upstream_node_id: str,
    downstream_node_id: str,
) -> None:
    """Prevent a decisive result from being reused for a different protection pair."""
    if result.status not in ("VERIFIED", "NOT VERIFIED"):
        return
    if result.provenance is None:
        raise ValueError(f"{result.status} result is invalid without provenance")
    expected = (upstream_node_id, downstream_node_id)
    if result.provenance.pair_key != expected:
        raise ValueError(
            "verification provenance belongs to a different protection relationship"
        )
