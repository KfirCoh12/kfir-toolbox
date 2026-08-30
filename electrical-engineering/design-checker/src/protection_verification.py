"""Strict contracts for future protection/selectivity verification engines.

This module deliberately does not implement engineering verification. It defines the
boundary a future verifier must cross before any backend path may claim ``VERIFIED``.
A verified result must identify the verifier, the exact protection pair, and traceable
provenance. Planning, topology, evidence-readiness, or rating order are not verifiers.
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


def make_unverified_result(
    *,
    check: VerificationCheck,
    requested: bool,
    missing_evidence: tuple[str, ...] = (),
    basis: str,
) -> ProtectionVerificationResult:
    """Construct a result that cannot claim engineering verification."""
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
    """Construct ``VERIFIED`` only when strict traceability is explicitly supplied.

    This constructor validates provenance shape only. It does not decide whether an
    engineering rule passes. A future dedicated verifier must perform that check and
    may call this function only after doing so.
    """
    if not _nonblank(provenance.upstream_node_id) or not _nonblank(provenance.downstream_node_id):
        raise ValueError("verified result requires upstream and downstream protection node IDs")
    if provenance.upstream_node_id == provenance.downstream_node_id:
        raise ValueError("verified result requires two distinct protection nodes")
    if not _nonblank(provenance.verifier.name) or not _nonblank(provenance.verifier.version):
        raise ValueError("verified result requires verifier name and version")
    if not provenance.evidence_sources:
        raise ValueError("verified result requires at least one traceable evidence source")
    for source in provenance.evidence_sources:
        if not _nonblank(source.reference):
            raise ValueError("verified result evidence sources require nonblank references")
    if not _nonblank(provenance.rule_basis_ref):
        raise ValueError("verified result requires a traceable rule basis reference")
    if not _nonblank(basis):
        raise ValueError("verified result requires a nonblank engineering basis")

    return ProtectionVerificationResult(
        check=check,
        status="VERIFIED",
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
    """Prevent a verified result from being reused for a different protection pair."""
    if result.status != "VERIFIED":
        return
    if result.provenance is None:
        raise ValueError("VERIFIED result is invalid without provenance")
    expected = (upstream_node_id, downstream_node_id)
    if result.provenance.pair_key != expected:
        raise ValueError(
            "verification provenance belongs to a different protection relationship"
        )
