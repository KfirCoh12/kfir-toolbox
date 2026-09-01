"""UI-neutral calculated view of the persisted Board Planner working board."""
from dataclasses import dataclass

from .board_graph import BoardElectricalGraph
from .branch_engine import FinalBranchDesignRequest, FinalBranchDesignResult, calculate_final_branch
from .field_rollup import FieldFeederRollup, calculate_field_rollups, enrich_graph_with_field_rollups
from .hierarchy_display import enrich_graph_with_hierarchy_plan
from .hierarchy_planner import BoardHierarchyPlanResult, calculate_board_hierarchy
from .working_board_graph import graph_from_working_board


@dataclass(frozen=True)
class WorkingCircuitContext:
    circuit_id: str
    design_current_a: float | None
    breaker_candidate_a: float | None
    cable_mm2: float | None
    cable_runs: int | None
    basis: str


@dataclass(frozen=True)
class CalculatedWorkingBoard:
    graph: BoardElectricalGraph
    hierarchy: BoardHierarchyPlanResult
    final_branches: tuple[FinalBranchDesignResult, ...]
    field_rollups: tuple[FieldFeederRollup, ...]
    circuit_contexts: tuple[WorkingCircuitContext, ...]

    @property
    def context_by_circuit_id(self) -> dict[str, WorkingCircuitContext]:
        return {item.circuit_id: item for item in self.circuit_contexts}


def _final_branch_request(payload: dict, branch: dict) -> FinalBranchDesignRequest:
    phase = str(branch.get("phase", "three"))
    voltage = float(
        payload.get("line_to_neutral_voltage_v", 230.0)
        if phase == "single"
        else payload.get("line_to_line_voltage_v", 400.0)
    )
    mode = str(branch.get("mode", "auto"))
    return FinalBranchDesignRequest(
        circuit_id=str(branch.get("circuit_id", "")).strip(),
        description=str(branch.get("description", "")).strip(),
        mode=mode,
        voltage_v=voltage,
        phase=phase,
        material=str(branch.get("material", "copper")),
        expected_load_kw=float(branch.get("load_kw", 0.0)) if mode == "auto" else None,
        connection_option_id=branch.get("connection_option_id") if mode == "manual" else None,
        power_factor=float(branch.get("power_factor", 1.0)),
        demand_factor=float(branch.get("demand_factor", 1.0)),
    )


def calculate_working_board(payload: dict) -> CalculatedWorkingBoard:
    """Re-run Board Planner calculations from the persisted working-board inputs.

    The function reuses the existing branch, hierarchy and field-rollup engines. It
    adds no protection claims and keeps all breaker/cable values as planning
    candidates until a dedicated verification says otherwise.
    """
    graph = graph_from_working_board(payload)
    branches = payload.get("branches", [])
    if not isinstance(branches, list):
        raise ValueError("working board branches must be a list")

    final_results: list[FinalBranchDesignResult] = []
    for branch in branches:
        if isinstance(branch, dict) and branch.get("kind") == "final":
            final_results.append(calculate_final_branch(_final_branch_request(payload, branch)))

    hierarchy = calculate_board_hierarchy(
        graph,
        circuit_request_overrides=tuple(result.circuit.request for result in final_results),
    )
    enriched = enrich_graph_with_hierarchy_plan(graph, hierarchy)

    field_materials = {
        str(branch.get("field_id", "")).strip(): str(branch.get("material", "copper"))
        for branch in branches
        if isinstance(branch, dict) and branch.get("kind") == "field"
    }
    field_rollups: tuple[FieldFeederRollup, ...] = tuple()
    root_plan = hierarchy.root.plan
    if root_plan is not None:
        field_rollups = calculate_field_rollups(graph, root_plan, field_materials)
        enriched = enrich_graph_with_field_rollups(enriched, field_rollups)

    contexts: dict[str, WorkingCircuitContext] = {}
    for result in final_results:
        contexts[result.request.circuit_id] = WorkingCircuitContext(
            circuit_id=result.request.circuit_id,
            design_current_a=result.design_current_a,
            breaker_candidate_a=result.breaker_a,
            cable_mm2=result.cable_mm2,
            cable_runs=result.cable_runs,
            basis="Calculated final branch from saved Board Planner inputs.",
        )

    for rollup in field_rollups:
        if rollup.status != "PROVISIONAL" or rollup.feeder_design is None:
            continue
        contexts[rollup.feeder_circuit_id] = WorkingCircuitContext(
            circuit_id=rollup.feeder_circuit_id,
            design_current_a=rollup.required_current_a,
            breaker_candidate_a=rollup.feeder_design.breaker_a,
            cable_mm2=rollup.feeder_design.cable_mm2,
            cable_runs=rollup.feeder_design.cable_runs,
            basis="Calculated field feeder roll-up from downstream planned phase demand.",
        )

    for rollup in hierarchy.feeder_rollups:
        contexts.setdefault(
            rollup.feeder_circuit_id,
            WorkingCircuitContext(
                circuit_id=rollup.feeder_circuit_id,
                design_current_a=rollup.required_current_a,
                breaker_candidate_a=rollup.breaker_candidate_a,
                cable_mm2=rollup.cable_candidate_mm2,
                cable_runs=rollup.cable_runs,
                basis="Calculated sub-board feeder roll-up from downstream board phase demand.",
            ),
        )

    return CalculatedWorkingBoard(
        graph=enriched,
        hierarchy=hierarchy,
        final_branches=tuple(final_results),
        field_rollups=field_rollups,
        circuit_contexts=tuple(contexts.values()),
    )
