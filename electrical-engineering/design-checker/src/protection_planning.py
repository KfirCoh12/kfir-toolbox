"""Backend integration of protection planning with board and feeder results.

This module adapts existing board-planning outputs to the conservative protection
primitives in :mod:`src.protection`. It intentionally keeps two different questions
separate:

1. What breaker rating is the load-sized planning candidate for the calculated
   design current?
2. Has protection or selectivity/coordination actually been checked?

The first question may produce a CANDIDATE from the declared breaker-rating catalog.
The second remains NOT CHECKED unless a check is requested, and a requested check
remains INSUFFICIENT DATA until real fault/device/manufacturer evidence is supplied.
No rating comparison is treated as selectivity evidence.
"""
from dataclasses import dataclass
from math import isclose
from typing import Literal

from .board_planner import BoardPlanResult
from .hierarchy_planner import BoardHierarchyPlanResult, SubBoardFeederRollup
from .protection import ProtectionPlan, build_protection_plan

ProtectionPlanningKind = Literal["BOARD_INCOMER", "SUB_BOARD_FEEDER"]


@dataclass(frozen=True)
class ProtectionPlanningRecord:
    """One protective-device planning record, separate from UI rendering."""

    kind: ProtectionPlanningKind
    device_ref: str
    board_id: str
    parent_board_id: str | None
    feeder_circuit_id: str | None
    plan: ProtectionPlan

    @property
    def design_current_a(self) -> float:
        return self.plan.candidate.design_current_a

    @property
    def breaker_candidate_a(self) -> float | None:
        return self.plan.candidate.breaker_rating_a


def _assert_candidate_consistency(
    *,
    context: str,
    plan: ProtectionPlan,
    existing_status: str,
    existing_rating_a: float | None,
) -> None:
    """Guard against two backend paths silently disagreeing on load sizing."""
    if existing_status in ("CANDIDATE", "PROVISIONAL"):
        if plan.candidate.status != "CANDIDATE" or existing_rating_a is None:
            raise ValueError(f"{context} breaker candidate disagrees with protection planner")
        if plan.candidate.breaker_rating_a is None or not isclose(
            plan.candidate.breaker_rating_a,
            float(existing_rating_a),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(f"{context} breaker candidate disagrees with protection planner")
        return

    if existing_status == "NO_CANDIDATE":
        if plan.candidate.status != "NO_CANDIDATE" or existing_rating_a is not None:
            raise ValueError(f"{context} no-candidate state disagrees with protection planner")
        return

    raise ValueError(f"unsupported {context} breaker-candidate status {existing_status}")


def board_incomer_protection_plan(
    board_plan: BoardPlanResult,
    *,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
) -> ProtectionPlan:
    """Return one board incomer plan without upgrading coordination claims."""
    candidate = board_plan.incomer_candidate
    plan = build_protection_plan(
        design_current_a=candidate.required_current_a,
        protection_check_requested=protection_check_requested,
        selectivity_check_requested=selectivity_check_requested,
    )
    _assert_candidate_consistency(
        context=f"board {board_plan.request.board_id} incomer",
        plan=plan,
        existing_status=candidate.status,
        existing_rating_a=candidate.breaker_rating_a,
    )
    return plan


def feeder_protection_plan(
    rollup: SubBoardFeederRollup,
    *,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
) -> ProtectionPlan | None:
    """Return an upstream feeder-device plan, or None when the feeder has no demand."""
    if rollup.status == "NO_DEMAND":
        if rollup.required_current_a != 0 or rollup.breaker_candidate_a is not None:
            raise ValueError(
                f"feeder {rollup.feeder_circuit_id} NO_DEMAND state contains breaker demand"
            )
        return None

    plan = build_protection_plan(
        design_current_a=rollup.required_current_a,
        protection_check_requested=protection_check_requested,
        selectivity_check_requested=selectivity_check_requested,
    )
    _assert_candidate_consistency(
        context=f"feeder {rollup.feeder_circuit_id}",
        plan=plan,
        existing_status=rollup.status,
        existing_rating_a=rollup.breaker_candidate_a,
    )
    return plan


def hierarchy_protection_plans(
    result: BoardHierarchyPlanResult,
    *,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
) -> tuple[ProtectionPlanningRecord, ...]:
    """Expose explicit incomer and feeder protection-planning records.

    Active board incomers and active sub-board feeder protective devices are included.
    Empty/no-demand boards and feeders do not synthesize a zero-current breaker plan.
    Coordination status is produced independently for every record and is never
    inferred from breaker-rating order in the hierarchy.
    """
    records: list[ProtectionPlanningRecord] = []

    for board in result.boards:
        if board.plan is None:
            continue
        plan = board_incomer_protection_plan(
            board.plan,
            protection_check_requested=protection_check_requested,
            selectivity_check_requested=selectivity_check_requested,
        )
        records.append(ProtectionPlanningRecord(
            kind="BOARD_INCOMER",
            device_ref=f"{board.board_id}:incomer",
            board_id=board.board_id,
            parent_board_id=board.parent_board_id,
            feeder_circuit_id=board.feeder_circuit_id,
            plan=plan,
        ))

    for rollup in result.feeder_rollups:
        plan = feeder_protection_plan(
            rollup,
            protection_check_requested=protection_check_requested,
            selectivity_check_requested=selectivity_check_requested,
        )
        if plan is None:
            continue
        records.append(ProtectionPlanningRecord(
            kind="SUB_BOARD_FEEDER",
            device_ref=f"{rollup.feeder_circuit_id}:device",
            board_id=rollup.board_id,
            parent_board_id=rollup.parent_board_id,
            feeder_circuit_id=rollup.feeder_circuit_id,
            plan=plan,
        ))

    return tuple(records)
