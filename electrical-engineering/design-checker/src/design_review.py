"""UI-neutral design-review issues for the calculated working board.

This module turns unresolved planning scope into explicit, targetable records for the
Board Planner. It deliberately does not create protection/selectivity verdicts and it
does not invent project thresholds. An ATTENTION item means the current design model
cannot complete a requested planning output; a LIMITATION records a known scope caveat
without calling the design a failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .working_board_plan import CalculatedWorkingBoard

DesignReviewSeverity = Literal["ATTENTION", "LIMITATION"]
DesignReviewScope = Literal["FINAL_CIRCUIT", "FIELD_FEEDER", "SUB_BOARD_FEEDER"]
DesignReviewCode = Literal[
    "BREAKER_CANDIDATE_UNAVAILABLE",
    "CABLE_CANDIDATE_UNAVAILABLE",
    "SINGLE_PHASE_CABLE_SCOPE",
    "FIELD_FEEDER_BREAKER_UNAVAILABLE",
    "FIELD_FEEDER_CABLE_UNAVAILABLE",
    "FIELD_FEEDER_MIXED_SINGLE_PHASE_SCOPE",
    "SUB_BOARD_FEEDER_BREAKER_UNAVAILABLE",
    "SUB_BOARD_FEEDER_CABLE_NOT_DECLARED",
    "SUB_BOARD_FEEDER_CABLE_NOT_VERIFIED",
    "SUB_BOARD_FEEDER_CABLE_NO_CANDIDATE",
]


@dataclass(frozen=True)
class DesignReviewIssue:
    code: DesignReviewCode
    severity: DesignReviewSeverity
    scope: DesignReviewScope
    target_id: str
    title: str
    detail: str
    route_circuit_id: str | None = None


@dataclass(frozen=True)
class DesignReviewSummary:
    issues: tuple[DesignReviewIssue, ...]

    @property
    def attention_count(self) -> int:
        return sum(issue.severity == "ATTENTION" for issue in self.issues)

    @property
    def limitation_count(self) -> int:
        return sum(issue.severity == "LIMITATION" for issue in self.issues)

    @property
    def issues_by_target(self) -> dict[str, tuple[DesignReviewIssue, ...]]:
        grouped: dict[str, list[DesignReviewIssue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.target_id, []).append(issue)
        return {key: tuple(value) for key, value in grouped.items()}


def _issue(
    code: DesignReviewCode,
    severity: DesignReviewSeverity,
    scope: DesignReviewScope,
    target_id: str,
    title: str,
    detail: str,
    *,
    route_circuit_id: str | None = None,
) -> DesignReviewIssue:
    return DesignReviewIssue(
        code=code,
        severity=severity,
        scope=scope,
        target_id=target_id,
        title=title,
        detail=detail,
        route_circuit_id=route_circuit_id,
    )


def _final_branch_issues(calculated: CalculatedWorkingBoard) -> list[DesignReviewIssue]:
    issues: list[DesignReviewIssue] = []
    for result in calculated.final_branches:
        circuit_id = result.request.circuit_id
        if result.breaker_a is None:
            issues.append(
                _issue(
                    "BREAKER_CANDIDATE_UNAVAILABLE",
                    "ATTENTION",
                    "FINAL_CIRCUIT",
                    circuit_id,
                    "Breaker candidate unresolved",
                    "The current planning catalog/inputs did not produce a load-sized breaker candidate. No breaker rating is invented.",
                    route_circuit_id=circuit_id,
                )
            )
        if result.cable_mm2 is None:
            if result.request.phase == "single":
                issues.append(
                    _issue(
                        "SINGLE_PHASE_CABLE_SCOPE",
                        "ATTENTION",
                        "FINAL_CIRCUIT",
                        circuit_id,
                        "Single-phase cable sizing needs input/model support",
                        "Automatic cable selection is outside the current single-phase cable dataset. The circuit current and breaker candidate remain separate planning outputs.",
                        route_circuit_id=circuit_id,
                    )
                )
            else:
                issues.append(
                    _issue(
                        "CABLE_CANDIDATE_UNAVAILABLE",
                        "ATTENTION",
                        "FINAL_CIRCUIT",
                        circuit_id,
                        "Cable candidate unresolved",
                        "The declared circuit conditions did not produce a supported automatic cable candidate. No cable size is guessed.",
                        route_circuit_id=circuit_id,
                    )
                )
    return issues


def _field_feeder_issues(calculated: CalculatedWorkingBoard) -> list[DesignReviewIssue]:
    issues: list[DesignReviewIssue] = []
    for rollup in calculated.field_rollups:
        if rollup.status != "PROVISIONAL" or rollup.feeder_design is None:
            continue
        feeder_id = rollup.feeder_circuit_id
        if rollup.feeder_design.breaker_a is None:
            issues.append(
                _issue(
                    "FIELD_FEEDER_BREAKER_UNAVAILABLE",
                    "ATTENTION",
                    "FIELD_FEEDER",
                    feeder_id,
                    "Field feeder breaker candidate unresolved",
                    "The bottom-up field demand did not produce a load-sized breaker candidate. No feeder rating is invented.",
                    route_circuit_id=feeder_id,
                )
            )
        if rollup.feeder_design.cable_mm2 is None:
            issues.append(
                _issue(
                    "FIELD_FEEDER_CABLE_UNAVAILABLE",
                    "ATTENTION",
                    "FIELD_FEEDER",
                    feeder_id,
                    "Field feeder cable candidate unresolved",
                    "The field roll-up did not produce a supported automatic feeder cable candidate. No feeder cable size is guessed.",
                    route_circuit_id=feeder_id,
                )
            )
        if rollup.contains_single_phase_loads:
            issues.append(
                _issue(
                    "FIELD_FEEDER_MIXED_SINGLE_PHASE_SCOPE",
                    "LIMITATION",
                    "FIELD_FEEDER",
                    feeder_id,
                    "Mixed single-phase field feeder scope",
                    "The feeder candidate reuses the current three-loaded-conductor planning route; neutral loading and harmonic effects from single-phase child circuits are not verified.",
                    route_circuit_id=feeder_id,
                )
            )
    return issues


def _sub_board_feeder_issues(calculated: CalculatedWorkingBoard) -> list[DesignReviewIssue]:
    issues: list[DesignReviewIssue] = []
    for rollup in calculated.hierarchy.feeder_rollups:
        if rollup.status == "NO_DEMAND":
            continue
        feeder_id = rollup.feeder_circuit_id
        if rollup.breaker_candidate_a is None:
            issues.append(
                _issue(
                    "SUB_BOARD_FEEDER_BREAKER_UNAVAILABLE",
                    "ATTENTION",
                    "SUB_BOARD_FEEDER",
                    feeder_id,
                    "Sub-board feeder breaker candidate unresolved",
                    "The downstream board demand did not produce a load-sized feeder breaker candidate. No rating is invented.",
                    route_circuit_id=feeder_id,
                )
            )
        if rollup.cable_status == "NOT_DECLARED":
            issues.append(
                _issue(
                    "SUB_BOARD_FEEDER_CABLE_NOT_DECLARED",
                    "ATTENTION",
                    "SUB_BOARD_FEEDER",
                    feeder_id,
                    "Sub-board feeder installation not declared",
                    "A feeder cable candidate is intentionally withheld until the feeder installation conditions are explicitly declared.",
                    route_circuit_id=feeder_id,
                )
            )
        elif rollup.cable_status == "NOT_VERIFIED":
            issues.append(
                _issue(
                    "SUB_BOARD_FEEDER_CABLE_NOT_VERIFIED",
                    "ATTENTION",
                    "SUB_BOARD_FEEDER",
                    feeder_id,
                    "Sub-board feeder cable scope unresolved",
                    "The declared feeder conditions remain outside the supported automatic cable-sizing scope; no cable candidate is promoted as verified.",
                    route_circuit_id=feeder_id,
                )
            )
        elif rollup.cable_status == "NO_CANDIDATE":
            issues.append(
                _issue(
                    "SUB_BOARD_FEEDER_CABLE_NO_CANDIDATE",
                    "ATTENTION",
                    "SUB_BOARD_FEEDER",
                    feeder_id,
                    "Sub-board feeder cable candidate unavailable",
                    "The supported feeder cable dataset did not produce a candidate for the declared demand and installation inputs. No size is invented.",
                    route_circuit_id=feeder_id,
                )
            )
    return issues


def design_review_summary(calculated: CalculatedWorkingBoard) -> DesignReviewSummary:
    """Return deterministic review issues for the current calculated board."""
    issues = (
        _final_branch_issues(calculated)
        + _field_feeder_issues(calculated)
        + _sub_board_feeder_issues(calculated)
    )
    severity_order = {"ATTENTION": 0, "LIMITATION": 1}
    scope_order = {"FINAL_CIRCUIT": 0, "FIELD_FEEDER": 1, "SUB_BOARD_FEEDER": 2}
    issues.sort(
        key=lambda item: (
            severity_order[item.severity],
            scope_order[item.scope],
            item.target_id,
            item.code,
        )
    )
    return DesignReviewSummary(tuple(issues))
