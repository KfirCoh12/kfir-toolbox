"""Conservative protection/selectivity planning primitives.

This module deliberately separates a load-sized breaker candidate from any claim
that protection or selectivity has been verified. A breaker rating selected only
because In >= Ib is a planning candidate, not a standards or manufacturer-backed
coordination verdict.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Literal, Sequence

from .catalogs import BREAKER_RATINGS_A

BreakerCandidateStatus = Literal["CANDIDATE", "NO_CANDIDATE"]
VerificationStatus = Literal[
    "NOT CHECKED",
    "INSUFFICIENT DATA",
    "VERIFIED",
    "NOT VERIFIED",
]


@dataclass(frozen=True)
class LoadSizedBreakerCandidate:
    design_current_a: float
    status: BreakerCandidateStatus
    breaker_rating_a: float | None
    basis: str


@dataclass(frozen=True)
class ProtectionCoordinationStatus:
    protection_status: VerificationStatus
    selectivity_status: VerificationStatus
    missing_evidence: tuple[str, ...]
    basis: str


@dataclass(frozen=True)
class ProtectionPlan:
    candidate: LoadSizedBreakerCandidate
    coordination: ProtectionCoordinationStatus


def load_sized_breaker_candidate(
    *,
    design_current_a: float,
    breaker_ratings_a: Sequence[float] = BREAKER_RATINGS_A,
) -> LoadSizedBreakerCandidate:
    """Return the first declared breaker rating at or above design current.

    This is intentionally only a numerical load-sizing candidate. It does not
    verify cable protection, fault protection, breaking capacity, discrimination,
    selectivity, manufacturer coordination, or any IEC requirement.
    """
    if not isfinite(design_current_a) or design_current_a <= 0:
        raise ValueError("design_current_a must be a finite value greater than 0")

    ratings = tuple(float(rating) for rating in breaker_ratings_a)
    if any(not isfinite(rating) or rating <= 0 for rating in ratings):
        raise ValueError("breaker ratings must be finite values greater than 0")
    if tuple(sorted(ratings)) != ratings:
        raise ValueError("breaker ratings must be in ascending order")

    rating = next((rating for rating in ratings if rating >= design_current_a), None)
    return LoadSizedBreakerCandidate(
        design_current_a=design_current_a,
        status="CANDIDATE" if rating is not None else "NO_CANDIDATE",
        breaker_rating_a=rating,
        basis=(
            "First declared breaker rating at or above design current (In >= Ib). "
            "This is a load-sized candidate only and is not protection or selectivity verification."
        ),
    )


def coordination_status(
    *,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
) -> ProtectionCoordinationStatus:
    """Return a conservative status until real evidence is available.

    Merely requesting a check cannot produce VERIFIED. Without verified device
    characteristics, fault data, and manufacturer/curve evidence, requested checks
    remain INSUFFICIENT DATA. Unrequested checks remain NOT CHECKED.
    """
    missing: list[str] = []
    protection_status: VerificationStatus = "NOT CHECKED"
    selectivity_status: VerificationStatus = "NOT CHECKED"

    if protection_check_requested:
        protection_status = "INSUFFICIENT DATA"
        missing.extend((
            "prospective fault current / fault-loop data at the protected point",
            "breaker device characteristics and breaking capacity",
            "cable protective constraints and verified rule basis",
        ))

    if selectivity_check_requested:
        selectivity_status = "INSUFFICIENT DATA"
        missing.extend((
            "upstream and downstream protective-device make/model/settings",
            "manufacturer selectivity/coordination table or verified time-current evidence",
        ))

    return ProtectionCoordinationStatus(
        protection_status=protection_status,
        selectivity_status=selectivity_status,
        missing_evidence=tuple(dict.fromkeys(missing)),
        basis=(
            "No protection or selectivity result is promoted to VERIFIED without real, "
            "traceable evidence. Numerical breaker load sizing is evaluated separately."
        ),
    )


def build_protection_plan(
    *,
    design_current_a: float,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
    breaker_ratings_a: Sequence[float] = BREAKER_RATINGS_A,
) -> ProtectionPlan:
    """Build a planning result while keeping candidate sizing and verification separate."""
    return ProtectionPlan(
        candidate=load_sized_breaker_candidate(
            design_current_a=design_current_a,
            breaker_ratings_a=breaker_ratings_a,
        ),
        coordination=coordination_status(
            protection_check_requested=protection_check_requested,
            selectivity_check_requested=selectivity_check_requested,
        ),
    )
