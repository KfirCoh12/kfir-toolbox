"""Bottom-up planning across nested board calculation boundaries.

Each board remains an independent calculation boundary. A downstream board's actual
L1/L2/L3 current vector is propagated to its parent as a BoardPhaseContribution,
not flattened into the parent's local circuit list and not replaced by a fictitious
balanced three-phase load.

Callers may also supply exact CircuitDesignRequest overrides for graph loads whose
real basis is fixed current or kVA. The hierarchy therefore preserves that basis
without converting it to an invented kW value.

Sub-board feeder cable sizing remains opt-in. A caller must explicitly declare the
feeder installation conditions, and automatic cable selection is only attempted when
the complete downstream hierarchy contains no single-phase final loads. This keeps
neutral/harmonic effects outside the automatic claim rather than silently treating a
mixed hierarchy as a three-loaded-conductor feeder.
"""
from dataclasses import dataclass, replace
from math import isfinite
from typing import Literal

from .board_boundaries import BoardCalculationBoundary, calculation_boundaries_from_graph
from .board_graph import BoardElectricalGraph, validate_board_graph
from .board_planner import (
    BoardPhaseContribution,
    BoardPlanRequest,
    BoardPlanResult,
    calculate_board_plan,
)
from .catalogs import BREAKER_RATINGS_A
from .circuit_engine import CircuitDesignRequest, calculate_circuit_design

HierarchyBoardStatus = Literal["CALCULATED", "NO_DEMAND"]
FeederRollupStatus = Literal["PROVISIONAL", "NO_DEMAND", "NO_CANDIDATE"]
FeederCableStatus = Literal[
    "NOT_DECLARED",
    "CANDIDATE",
    "NOT_VERIFIED",
    "NO_CANDIDATE",
    "NOT_APPLICABLE",
]


@dataclass(frozen=True)
class FeederInstallationDeclaration:
    """Explicit installation inputs for one sub-board feeder.

    These values do not expand the supported engineering dataset. They only allow the
    existing circuit engine to be reused when the declared conditions fit its narrow
    automatic Method E / three-loaded-conductor scope.

    Voltage-drop calculation is optional. If ``length_m`` is supplied, Annex G
    resistivity/reactance defaults must currently be explicitly enabled because the
    feeder declaration does not yet carry user-supplied conductor impedance data.
    ``power_factor`` may still be supplied explicitly; otherwise Annex G's PF default
    is also used when defaults are enabled.
    """

    feeder_circuit_id: str
    material: Literal["copper", "aluminium"] = "copper"
    ambient_temperature_c: float = 30.0
    grouped_circuits: int = 1
    grouping_arrangement: str | None = None
    parallel_runs: int = 1
    equal_current_sharing_confirmed: bool | None = None
    length_m: float | None = None
    power_factor: float | None = None
    permitted_voltage_drop_percent: float | None = None
    voltage_drop_limit_source: str | None = None
    allow_annex_g_defaults: bool = False
    basis_note: str = ""


@dataclass(frozen=True)
class HierarchyBoardResult:
    board_id: str
    parent_board_id: str | None
    feeder_circuit_id: str | None
    status: HierarchyBoardStatus
    plan: BoardPlanResult | None
    child_board_ids: tuple[str, ...]
    contains_single_phase_loads: bool


@dataclass(frozen=True)
class SubBoardFeederRollup:
    board_id: str
    parent_board_id: str
    feeder_circuit_id: str
    status: FeederRollupStatus
    l1_current_a: float
    l2_current_a: float
    l3_current_a: float
    required_current_a: float
    breaker_candidate_a: float | None
    cable_status: FeederCableStatus
    cable_candidate_mm2: float | None
    cable_runs: int | None
    feeder_scope_status: str | None
    installation_declared: bool
    basis: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class BoardHierarchyPlanResult:
    boards: tuple[HierarchyBoardResult, ...]
    feeder_rollups: tuple[SubBoardFeederRollup, ...]

    @property
    def plans(self) -> tuple[BoardPlanResult, ...]:
        return tuple(board.plan for board in self.boards if board.plan is not None)

    @property
    def plans_by_board_id(self) -> dict[str, BoardPlanResult]:
        return {
            board.board_id: board.plan
            for board in self.boards
            if board.plan is not None
        }

    @property
    def root(self) -> HierarchyBoardResult:
        roots = tuple(board for board in self.boards if board.parent_board_id is None)
        if len(roots) != 1:
            raise ValueError("hierarchy result must contain exactly one root board")
        return roots[0]


def _parent_board_id(
    graph: BoardElectricalGraph,
    boundary: BoardCalculationBoundary,
) -> str | None:
    if boundary.feeder_circuit_id is None:
        return None
    anchor = graph.node_by_id[boundary.anchor_node_id]
    if anchor.kind != "sub_board":
        raise ValueError(f"downstream board {boundary.board_id} anchor must be a sub_board")
    for ancestor in graph.ancestors_of(anchor.node_id):
        if ancestor.kind == "busbar" and ancestor.board_ref:
            return ancestor.board_ref.strip()
    raise ValueError(f"downstream board {boundary.board_id} has no parent board busbar")


def _base_request(
    graph: BoardElectricalGraph,
    boundary: BoardCalculationBoundary,
    contributions: tuple[BoardPhaseContribution, ...],
) -> BoardPlanRequest | None:
    if boundary.request is None and not contributions:
        return None
    if boundary.request is None:
        return BoardPlanRequest(
            board_id=boundary.board_id,
            description=boundary.description,
            circuits=tuple(),
            line_to_line_voltage_v=graph.line_to_line_voltage_v,
            line_to_neutral_voltage_v=graph.line_to_neutral_voltage_v,
            phase_contributions=contributions,
        )
    return replace(boundary.request, phase_contributions=contributions)


def _contribution_from_child(
    child_board_id: str,
    feeder_circuit_id: str,
    child_plan: BoardPlanResult,
) -> BoardPhaseContribution:
    balance = child_plan.phase_balance
    return BoardPhaseContribution(
        contribution_id=feeder_circuit_id,
        l1_current_a=balance.l1_current_a,
        l2_current_a=balance.l2_current_a,
        l3_current_a=balance.l3_current_a,
        basis=(
            f"Calculated downstream board {child_board_id} phase demand propagated "
            "without additional hierarchy-level diversity."
        ),
    )


def _validate_feeder_installation(declaration: FeederInstallationDeclaration) -> None:
    if not declaration.feeder_circuit_id.strip():
        raise ValueError("feeder installation feeder_circuit_id is required")
    if declaration.material not in ("copper", "aluminium"):
        raise ValueError("feeder installation material must be copper or aluminium")
    if not isfinite(declaration.ambient_temperature_c):
        raise ValueError("feeder installation ambient temperature must be finite")
    if declaration.grouped_circuits <= 0:
        raise ValueError("feeder installation grouped_circuits must be greater than 0")
    if declaration.parallel_runs <= 0:
        raise ValueError("feeder installation parallel_runs must be greater than 0")
    if declaration.length_m is not None:
        if not isfinite(declaration.length_m) or declaration.length_m <= 0:
            raise ValueError("feeder installation length_m must be finite and greater than 0")
        if not declaration.allow_annex_g_defaults:
            raise ValueError(
                "feeder voltage-drop calculation currently requires explicit "
                "allow_annex_g_defaults=True because feeder conductor impedance "
                "inputs are not yet represented"
            )
    elif declaration.permitted_voltage_drop_percent is not None:
        raise ValueError("feeder voltage-drop limit requires length_m")
    elif declaration.voltage_drop_limit_source is not None:
        raise ValueError("feeder voltage-drop limit source requires length_m")
    if declaration.power_factor is not None:
        if not isfinite(declaration.power_factor) or not 0 < declaration.power_factor <= 1:
            raise ValueError("feeder installation power_factor must be greater than 0 and at most 1")
        if declaration.length_m is None:
            raise ValueError("feeder installation power_factor is only used when length_m is declared")
    if declaration.permitted_voltage_drop_percent is not None:
        if (
            not isfinite(declaration.permitted_voltage_drop_percent)
            or declaration.permitted_voltage_drop_percent <= 0
        ):
            raise ValueError(
                "feeder permitted_voltage_drop_percent must be finite and greater than 0"
            )
        if not (declaration.voltage_drop_limit_source or "").strip():
            raise ValueError("feeder voltage-drop limit source is required when a limit is declared")
    if not declaration.basis_note.strip():
        raise ValueError("feeder installation basis_note is required")


def _feeder_rollup(
    graph: BoardElectricalGraph,
    board: HierarchyBoardResult,
    installation: FeederInstallationDeclaration | None,
) -> SubBoardFeederRollup:
    if board.parent_board_id is None or board.feeder_circuit_id is None:
        raise ValueError("root board does not have an upstream feeder rollup")
    if board.plan is None:
        return SubBoardFeederRollup(
            board_id=board.board_id,
            parent_board_id=board.parent_board_id,
            feeder_circuit_id=board.feeder_circuit_id,
            status="NO_DEMAND",
            l1_current_a=0.0,
            l2_current_a=0.0,
            l3_current_a=0.0,
            required_current_a=0.0,
            breaker_candidate_a=None,
            cable_status="NOT_APPLICABLE",
            cable_candidate_mm2=None,
            cable_runs=None,
            feeder_scope_status=None,
            installation_declared=installation is not None,
            basis="Downstream board has no calculated local or child-board demand.",
            limitations=("No feeder demand is synthesized for an empty downstream board.",),
        )

    balance = board.plan.phase_balance
    required = balance.max_phase_current_a
    rating = next((float(value) for value in BREAKER_RATINGS_A if value >= required), None)
    base_limitations = [
        "Breaker rating is a conventional planning candidate only; protection and selectivity are not verified.",
        "L1/L2/L3 are assumed phase-aligned between parent and child boards; transformer phase shift is not modeled.",
    ]

    if installation is None:
        base_limitations.insert(
            1,
            "Feeder cable is not sized because feeder material and installation conditions were not declared.",
        )
        return SubBoardFeederRollup(
            board_id=board.board_id,
            parent_board_id=board.parent_board_id,
            feeder_circuit_id=board.feeder_circuit_id,
            status="PROVISIONAL" if rating is not None else "NO_CANDIDATE",
            l1_current_a=balance.l1_current_a,
            l2_current_a=balance.l2_current_a,
            l3_current_a=balance.l3_current_a,
            required_current_a=required,
            breaker_candidate_a=rating,
            cable_status="NOT_DECLARED",
            cable_candidate_mm2=None,
            cable_runs=None,
            feeder_scope_status=None,
            installation_declared=False,
            basis=(
                "Highest calculated downstream-board phase current, with no additional "
                "hierarchy-level diversity."
            ),
            limitations=tuple(base_limitations),
        )

    if board.contains_single_phase_loads:
        base_limitations.insert(
            1,
            "Automatic feeder cable selection is not verified because the downstream hierarchy contains single-phase loads; neutral loading and harmonic effects are not modeled by the three-loaded-conductor dataset.",
        )
        return SubBoardFeederRollup(
            board_id=board.board_id,
            parent_board_id=board.parent_board_id,
            feeder_circuit_id=board.feeder_circuit_id,
            status="PROVISIONAL" if rating is not None else "NO_CANDIDATE",
            l1_current_a=balance.l1_current_a,
            l2_current_a=balance.l2_current_a,
            l3_current_a=balance.l3_current_a,
            required_current_a=required,
            breaker_candidate_a=rating,
            cable_status="NOT_VERIFIED",
            cable_candidate_mm2=None,
            cable_runs=None,
            feeder_scope_status="NOT_VERIFIED",
            installation_declared=True,
            basis=(
                "Highest calculated downstream-board phase current, with no additional "
                "hierarchy-level diversity."
            ),
            limitations=tuple(base_limitations),
        )

    design = calculate_circuit_design(CircuitDesignRequest(
        circuit_id=board.feeder_circuit_id,
        description=f"{board.board_id} feeder",
        load_type="a",
        load_value=required,
        voltage_v=graph.line_to_line_voltage_v,
        phase="three",
        power_factor=installation.power_factor,
        demand_factor=1.0,
        material=installation.material,
        ambient_temperature_c=installation.ambient_temperature_c,
        grouped_circuits=installation.grouped_circuits,
        grouping_arrangement=installation.grouping_arrangement,
        parallel_runs=installation.parallel_runs,
        equal_current_sharing_confirmed=installation.equal_current_sharing_confirmed,
        length_m=installation.length_m,
        permitted_voltage_drop_percent=installation.permitted_voltage_drop_percent,
        voltage_drop_limit_source=installation.voltage_drop_limit_source,
        allow_annex_g_defaults=installation.allow_annex_g_defaults,
    ))
    if design.breaker_a != rating:
        raise ValueError("feeder breaker candidate disagrees with shared circuit engine")

    if design.cable_mm2 is not None:
        cable_status: FeederCableStatus = "CANDIDATE"
    elif design.selection.status == "NO SUPPORTED SOLUTION":
        cable_status = "NO_CANDIDATE"
    else:
        cable_status = "NOT_VERIFIED"

    base_limitations.insert(
        1,
        "Feeder cable candidate reuses the existing automatic three-phase circuit engine under the explicitly declared installation conditions.",
    )
    base_limitations.extend(design.selection.limitations)
    return SubBoardFeederRollup(
        board_id=board.board_id,
        parent_board_id=board.parent_board_id,
        feeder_circuit_id=board.feeder_circuit_id,
        status="PROVISIONAL" if rating is not None else "NO_CANDIDATE",
        l1_current_a=balance.l1_current_a,
        l2_current_a=balance.l2_current_a,
        l3_current_a=balance.l3_current_a,
        required_current_a=required,
        breaker_candidate_a=rating,
        cable_status=cable_status,
        cable_candidate_mm2=design.cable_mm2,
        cable_runs=design.cable_runs,
        feeder_scope_status=design.verification.scope_status,
        installation_declared=True,
        basis=(
            "Highest calculated downstream-board phase current, with no additional "
            "hierarchy-level diversity. "
            f"Installation basis: {installation.basis_note.strip()}"
        ),
        limitations=tuple(dict.fromkeys(base_limitations)),
    )


def calculate_board_hierarchy(
    graph: BoardElectricalGraph,
    circuit_request_overrides: tuple[CircuitDesignRequest, ...] = tuple(),
    feeder_installations: tuple[FeederInstallationDeclaration, ...] = tuple(),
) -> BoardHierarchyPlanResult:
    """Calculate every board bottom-up and propagate child phase vectors upstream.

    Exact circuit overrides are passed into boundary construction before any board is
    solved. A fixed-A or kVA load therefore remains fixed-A or kVA at every hierarchy
    depth and in generated schedule rows.

    Feeder installation declarations are optional. Without one, the hierarchy still
    returns demand and a conventional breaker candidate but intentionally leaves the
    feeder cable unresolved.
    """
    validate_board_graph(graph)
    boundaries = calculation_boundaries_from_graph(graph, circuit_request_overrides)
    boundary_by_id = {boundary.board_id: boundary for boundary in boundaries}
    if len(boundary_by_id) != len(boundaries):
        raise ValueError("board calculation boundaries must have unique board_id values")

    parent_by_id = {
        boundary.board_id: _parent_board_id(graph, boundary)
        for boundary in boundaries
    }
    children_by_id: dict[str, list[str]] = {board_id: [] for board_id in boundary_by_id}
    for board_id, parent_id in parent_by_id.items():
        if parent_id is None:
            continue
        if parent_id not in boundary_by_id:
            raise ValueError(f"board {board_id} references unknown parent board {parent_id}")
        children_by_id[parent_id].append(board_id)

    roots = tuple(board_id for board_id, parent_id in parent_by_id.items() if parent_id is None)
    if len(roots) != 1 or roots[0] != graph.board_id.strip():
        raise ValueError("hierarchy must resolve exactly one root board matching graph.board_id")

    valid_feeder_ids = {
        boundary.feeder_circuit_id
        for boundary in boundaries
        if boundary.feeder_circuit_id is not None
    }
    installation_by_feeder: dict[str, FeederInstallationDeclaration] = {}
    for declaration in feeder_installations:
        _validate_feeder_installation(declaration)
        feeder_id = declaration.feeder_circuit_id.strip()
        if feeder_id in installation_by_feeder:
            raise ValueError(f"duplicate feeder installation declaration for {feeder_id}")
        if feeder_id not in valid_feeder_ids:
            raise ValueError(f"feeder installation references unknown sub-board feeder {feeder_id}")
        installation_by_feeder[feeder_id] = declaration

    solved: dict[str, HierarchyBoardResult] = {}
    visiting: set[str] = set()

    def solve(board_id: str) -> HierarchyBoardResult:
        if board_id in solved:
            return solved[board_id]
        if board_id in visiting:
            raise ValueError("board hierarchy contains a board-boundary cycle")
        visiting.add(board_id)

        boundary = boundary_by_id[board_id]
        child_ids = tuple(children_by_id[board_id])
        contributions: list[BoardPhaseContribution] = []
        child_results: list[HierarchyBoardResult] = []
        for child_id in child_ids:
            child = solve(child_id)
            child_results.append(child)
            if child.plan is None:
                continue
            if child.feeder_circuit_id is None:
                raise ValueError(f"downstream board {child_id} requires feeder_circuit_id")
            contributions.append(
                _contribution_from_child(child_id, child.feeder_circuit_id, child.plan)
            )

        request = _base_request(graph, boundary, tuple(contributions))
        plan = calculate_board_plan(request) if request is not None else None
        local_single_phase = bool(
            plan is not None and any(circuit.request.phase == "single" for circuit in plan.circuits)
        )
        contains_single_phase = local_single_phase or any(
            child.contains_single_phase_loads for child in child_results
        )
        result = HierarchyBoardResult(
            board_id=board_id,
            parent_board_id=parent_by_id[board_id],
            feeder_circuit_id=boundary.feeder_circuit_id,
            status="CALCULATED" if plan is not None else "NO_DEMAND",
            plan=plan,
            child_board_ids=child_ids,
            contains_single_phase_loads=contains_single_phase,
        )
        solved[board_id] = result
        visiting.remove(board_id)
        return result

    solve(roots[0])
    ordered_boards = tuple(solved[boundary.board_id] for boundary in boundaries)
    feeder_rollups = tuple(
        _feeder_rollup(
            graph,
            board,
            installation_by_feeder.get(board.feeder_circuit_id or ""),
        )
        for board in ordered_boards
        if board.parent_board_id is not None
    )
    return BoardHierarchyPlanResult(ordered_boards, feeder_rollups)
