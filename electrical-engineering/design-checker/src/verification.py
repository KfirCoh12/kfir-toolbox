"""Structured verification summaries for backend result objects.

This module translates existing calculation outcomes into stable machine-readable
scope states and issue codes. It does not add engineering rules, change numeric
results, or claim full standards compliance.
"""
from dataclasses import dataclass
from typing import Literal

from .circuit_selector import CircuitSelectionResult
from .max_load import MaxLoadResult

ScopeStatus = Literal["SUPPORTED_SCOPE", "PARTIAL_SCOPE", "NOT_VERIFIED"]
IssueCategory = Literal[
    "protection",
    "cable_ampacity",
    "connection",
    "voltage_drop",
    "input_coverage",
    "dataset",
]


@dataclass(frozen=True)
class VerificationIssue:
    code: str
    category: IssueCategory
    message: str
    blocking: bool


@dataclass(frozen=True)
class ResultVerification:
    scope_status: ScopeStatus
    issues: tuple[VerificationIssue, ...]

    @property
    def blocking_issues(self) -> tuple[VerificationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.blocking)


def _dedupe(issues: list[VerificationIssue]) -> tuple[VerificationIssue, ...]:
    seen: set[tuple[str, str]] = set()
    unique: list[VerificationIssue] = []
    for issue in issues:
        key = (issue.code, issue.message)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return tuple(unique)


def summarize_circuit_selection_verification(
    result: CircuitSelectionResult,
) -> ResultVerification:
    """Describe automatic circuit-selection coverage without re-running sizing logic."""
    issues: list[VerificationIssue] = []

    if result.suggested_breaker_a is not None:
        issues.append(VerificationIssue(
            code="protection_standard_not_implemented",
            category="protection",
            message=(
                "Breaker selection is a conventional numerical candidate; the IEC 60364-4-43 "
                "protection verification rule is not yet implemented."
            ),
            blocking=False,
        ))
    else:
        issues.append(VerificationIssue(
            code="breaker_catalog_exhausted",
            category="protection",
            message="No declared breaker candidate is available at or above the design current.",
            blocking=True,
        ))

    if result.suggested_connection is not None:
        issues.append(VerificationIssue(
            code="connection_configuration_not_verified",
            category="connection",
            message=(
                "The connection rating class is mapped, but exact accessory configuration and "
                "product compliance remain outside the current calculation scope."
            ),
            blocking=False,
        ))

    for limitation in result.limitations:
        lower = limitation.lower()
        if "three-phase / three-loaded-conductor" in lower:
            issues.append(VerificationIssue(
                code="cable_dataset_phase_unsupported",
                category="dataset",
                message=limitation,
                blocking=True,
            ))
        elif "explicit confirmation of acceptable current sharing" in lower:
            issues.append(VerificationIssue(
                code="parallel_current_sharing_not_confirmed",
                category="cable_ampacity",
                message=limitation,
                blocking=True,
            ))
        elif "must include at least all parallel runs" in lower:
            issues.append(VerificationIssue(
                code="parallel_grouping_incomplete",
                category="cable_ampacity",
                message=limitation,
                blocking=True,
            ))
        elif lower.startswith("cable ampacity not verified:"):
            issues.append(VerificationIssue(
                code="cable_ampacity_not_verified",
                category="cable_ampacity",
                message=limitation,
                blocking=True,
            ))
        elif "no sourced permitted limit was checked" in lower:
            issues.append(VerificationIssue(
                code="voltage_drop_limit_not_verified",
                category="voltage_drop",
                message=limitation,
                blocking=False,
            ))
        elif "unequal sharing or dissimilar runs are outside this model" in lower:
            issues.append(VerificationIssue(
                code="parallel_voltage_drop_model_limited",
                category="voltage_drop",
                message=limitation,
                blocking=False,
            ))

    if result.status == "SUGGESTION":
        scope_status: ScopeStatus = "SUPPORTED_SCOPE"
    elif result.status == "NO SUPPORTED SOLUTION":
        scope_status = "SUPPORTED_SCOPE"
        issues.append(VerificationIssue(
            code="no_supported_solution",
            category="dataset",
            message=(
                "The requested conditions are inside the implemented scope, but no candidate in "
                "the explicit dataset passed the implemented checks."
            ),
            blocking=True,
        ))
    else:
        scope_status = "PARTIAL_SCOPE"
        if not any(issue.blocking for issue in issues):
            issues.append(VerificationIssue(
                code="automatic_selection_not_verified",
                category="dataset",
                message="Automatic cable selection is not verified for the requested conditions.",
                blocking=True,
            ))

    return ResultVerification(scope_status, _dedupe(issues))


def summarize_max_load_verification(result: MaxLoadResult) -> ResultVerification:
    """Describe reverse-capacity coverage without changing the calculated ceiling."""
    issues: list[VerificationIssue] = []

    missing_map = (
        ("Breaker / upstream protection was not provided.", "missing_breaker_check", "protection"),
        ("Outlet / connection rating was not provided.", "missing_connection_check", "connection"),
        ("Cable ampacity was not provided or checked.", "missing_cable_check", "cable_ampacity"),
        (
            "The selected fixed connection has no generic numerical current ceiling",
            "fixed_connection_capacity_not_verified",
            "connection",
        ),
        (
            "Cable ampacity could not be verified for the supplied conditions.",
            "cable_ampacity_not_verified",
            "cable_ampacity",
        ),
    )
    for missing in result.missing_core_checks:
        matched = False
        for prefix, code, category in missing_map:
            if missing.startswith(prefix):
                issues.append(VerificationIssue(code, category, missing, True))
                matched = True
                break
        if not matched:
            issues.append(VerificationIssue(
                "missing_core_check",
                "input_coverage",
                missing,
                True,
            ))

    for limitation in result.limitations:
        lower = limitation.lower()
        if "60364-4-43" in lower:
            issues.append(VerificationIssue(
                "protection_standard_not_implemented",
                "protection",
                limitation,
                False,
            ))
        elif "product/standard-specific suitability" in lower or "exact accessory configuration" in lower:
            issues.append(VerificationIssue(
                "connection_configuration_not_verified",
                "connection",
                limitation,
                False,
            ))
        elif "voltage-drop geometry/material is required" in lower:
            issues.append(VerificationIssue(
                "voltage_drop_geometry_missing",
                "voltage_drop",
                limitation,
                True,
            ))
        elif "permitted voltage-drop limit and source are required" in lower:
            issues.append(VerificationIssue(
                "voltage_drop_limit_missing",
                "voltage_drop",
                limitation,
                True,
            ))
        elif "at least one supported current-limiting constraint is required" in lower:
            issues.append(VerificationIssue(
                "no_usable_constraint",
                "input_coverage",
                limitation,
                True,
            ))

    if result.status == "NOT VERIFIED":
        scope_status: ScopeStatus = "NOT_VERIFIED"
    elif result.coverage_status == "FULL CORE COVERAGE":
        scope_status = "SUPPORTED_SCOPE"
    else:
        scope_status = "PARTIAL_SCOPE"

    return ResultVerification(scope_status, _dedupe(issues))
