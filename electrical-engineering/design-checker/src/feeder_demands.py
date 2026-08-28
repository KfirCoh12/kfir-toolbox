"""Neutral contract for carrying downstream-board demand toward a feeder.

This module deliberately does not calculate diversity, feeder current, protection,
or selectivity. It only makes the unresolved boundary explicit and provides a typed
place for a future user-supplied or externally-derived demand value to be attached.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .board_summaries import BoardHierarchySummary

FeederDemandContractStatus = Literal[
    "ROOT_BOARD",
    "WAITING_FOR_LOCAL_CALCULATION",
    "AWAITING_DEMAND_INPUT",
    "DEMAND_DECLARED",
]
FeederDemandBasis = Literal["USER_DECLARED", "EXTERNAL_RULE"]


@dataclass(frozen=True)
class FeederDemandDeclaration:
    """An explicit feeder-demand value supplied from outside this module.

    `EXTERNAL_RULE` means some other reviewed calculation/rule produced the value;
    this module neither defines nor validates that engineering method. A non-empty
    note is required so the origin is never silently lost.
    """

    board_id: str
    demand_current_a: float
    basis: FeederDemandBasis
    basis_note: str


@dataclass(frozen=True)
class FeederDemandContract:
    board_id: str
    feeder_circuit_id: str | None
    status: FeederDemandContractStatus
    local_calculation_available: bool
    local_max_phase_current_reference_a: float | None
    declared_demand_current_a: float | None
    declaration_basis: FeederDemandBasis | None
    declaration_note: str | None

    @property
    def has_declared_demand(self) -> bool:
        return self.status == "DEMAND_DECLARED"


def _validate_declaration(declaration: FeederDemandDeclaration) -> None:
    board_id = declaration.board_id.strip()
    if not board_id:
        raise ValueError("feeder demand declaration board_id is required")
    if not isfinite(declaration.demand_current_a) or declaration.demand_current_a <= 0:
        raise ValueError("feeder demand declaration current must be finite and greater than 0")
    if declaration.basis not in ("USER_DECLARED", "EXTERNAL_RULE"):
        raise ValueError("unsupported feeder demand declaration basis")
    if not declaration.basis_note.strip():
        raise ValueError("feeder demand declaration basis_note is required")


def feeder_demand_contracts(
    summaries: tuple[BoardHierarchySummary, ...],
    declarations: tuple[FeederDemandDeclaration, ...] = tuple(),
) -> tuple[FeederDemandContract, ...]:
    """Build one feeder-demand contract per board summary.

    Local maximum phase current is exposed only as a reference. It is never copied
    into `declared_demand_current_a`; doing so would silently assert an aggregation
    method. Downstream boards therefore remain AWAITING_DEMAND_INPUT until a caller
    explicitly supplies a declaration with provenance.
    """
    summaries_by_id = {summary.board_id: summary for summary in summaries}
    if len(summaries_by_id) != len(summaries):
        raise ValueError("board hierarchy summaries must have unique board_id values")

    declarations_by_id: dict[str, FeederDemandDeclaration] = {}
    for declaration in declarations:
        _validate_declaration(declaration)
        board_id = declaration.board_id.strip()
        if board_id in declarations_by_id:
            raise ValueError(f"duplicate feeder demand declaration for {board_id}")
        summary = summaries_by_id.get(board_id)
        if summary is None:
            raise ValueError(f"feeder demand declaration board {board_id} is not in hierarchy summaries")
        if summary.feeder_circuit_id is None:
            raise ValueError(f"root board {board_id} does not have an upstream feeder demand")
        declarations_by_id[board_id] = declaration

    contracts: list[FeederDemandContract] = []
    for summary in summaries:
        local_reference = (
            max(summary.l1_current_a, summary.l2_current_a, summary.l3_current_a)
            if summary.has_local_calculation
            and summary.l1_current_a is not None
            and summary.l2_current_a is not None
            and summary.l3_current_a is not None
            else None
        )

        if summary.feeder_circuit_id is None:
            contracts.append(FeederDemandContract(
                board_id=summary.board_id,
                feeder_circuit_id=None,
                status="ROOT_BOARD",
                local_calculation_available=summary.has_local_calculation,
                local_max_phase_current_reference_a=local_reference,
                declared_demand_current_a=None,
                declaration_basis=None,
                declaration_note=None,
            ))
            continue

        declaration = declarations_by_id.get(summary.board_id)
        if declaration is not None:
            contracts.append(FeederDemandContract(
                board_id=summary.board_id,
                feeder_circuit_id=summary.feeder_circuit_id,
                status="DEMAND_DECLARED",
                local_calculation_available=summary.has_local_calculation,
                local_max_phase_current_reference_a=local_reference,
                declared_demand_current_a=declaration.demand_current_a,
                declaration_basis=declaration.basis,
                declaration_note=declaration.basis_note.strip(),
            ))
        else:
            contracts.append(FeederDemandContract(
                board_id=summary.board_id,
                feeder_circuit_id=summary.feeder_circuit_id,
                status=(
                    "AWAITING_DEMAND_INPUT"
                    if summary.has_local_calculation
                    else "WAITING_FOR_LOCAL_CALCULATION"
                ),
                local_calculation_available=summary.has_local_calculation,
                local_max_phase_current_reference_a=local_reference,
                declared_demand_current_a=None,
                declaration_basis=None,
                declaration_note=None,
            ))

    return tuple(contracts)
