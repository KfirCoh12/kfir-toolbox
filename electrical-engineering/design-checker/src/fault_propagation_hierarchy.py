"""Map root-busbar fault context through protective-device relationships.

Each downstream relationship inherits the fault current at its upstream protective
device and, when the intervening protected cable is described, applies the narrow
resistance-only screening model from :mod:`fault_propagation`.
"""
from dataclasses import dataclass
from typing import Mapping

from .board_graph import BoardElectricalGraph
from .fault_propagation import CableFaultPath, propagate_three_phase_fault_screening
from .protection_hierarchy import ProtectionPairKey, ProtectionRelationship


@dataclass(frozen=True)
class PairFaultContext:
    pair_key: ProtectionPairKey
    prospective_fault_current_ka: float | None
    basis: str
    path_circuit_id: str | None
    missing_inputs: tuple[str, ...] = tuple()



def _is_root_busbar_pair(graph: BoardElectricalGraph, relationship: ProtectionRelationship) -> bool:
    upstream = graph.node_by_id.get(relationship.upstream_node_id)
    return bool(
        upstream is not None
        and upstream.kind == "incomer"
        and (upstream.board_ref or "").strip() == graph.board_id.strip()
    )


def relationship_fault_contexts(
    graph: BoardElectricalGraph,
    relationships: tuple[ProtectionRelationship, ...],
    *,
    root_busbar_fault_current_ka: float | None,
    cable_path_by_circuit_id: Mapping[str, CableFaultPath] | None = None,
) -> tuple[PairFaultContext, ...]:
    """Return fault-current context for each protection relationship.

    Root-busbar relationships receive the declared/calculated main-board fault level.
    A non-root relationship is downstream of the cable protected by its upstream
    device. That cable is identified by the parent protection relationship's
    ``downstream_circuit_id``. Missing path information remains explicit.
    """
    cable_paths = dict(cable_path_by_circuit_id or {})
    by_downstream_node = {item.downstream_node_id: item for item in relationships}
    contexts: dict[ProtectionPairKey, PairFaultContext] = {}

    for relationship in relationships:
        if not _is_root_busbar_pair(graph, relationship):
            continue
        if root_busbar_fault_current_ka is None:
            contexts[relationship.pair_key] = PairFaultContext(
                pair_key=relationship.pair_key,
                prospective_fault_current_ka=None,
                basis="Main-board prospective fault current is not available.",
                path_circuit_id=None,
                missing_inputs=("main-board prospective fault current",),
            )
        else:
            contexts[relationship.pair_key] = PairFaultContext(
                pair_key=relationship.pair_key,
                prospective_fault_current_ka=float(root_busbar_fault_current_ka),
                basis="Fault current applies at the main-board busbar before downstream feeder impedance.",
                path_circuit_id=None,
            )

    unresolved = [item for item in relationships if item.pair_key not in contexts]
    while unresolved:
        progressed = False
        next_unresolved: list[ProtectionRelationship] = []
        for relationship in unresolved:
            parent = by_downstream_node.get(relationship.upstream_node_id)
            if parent is None:
                contexts[relationship.pair_key] = PairFaultContext(
                    pair_key=relationship.pair_key,
                    prospective_fault_current_ka=None,
                    basis="Could not identify the upstream protective relationship for this fault path.",
                    path_circuit_id=None,
                    missing_inputs=("upstream protection relationship",),
                )
                progressed = True
                continue

            parent_context = contexts.get(parent.pair_key)
            if parent_context is None:
                next_unresolved.append(relationship)
                continue
            if parent_context.prospective_fault_current_ka is None:
                contexts[relationship.pair_key] = PairFaultContext(
                    pair_key=relationship.pair_key,
                    prospective_fault_current_ka=None,
                    basis="Upstream fault current is unresolved, so downstream propagation cannot run.",
                    path_circuit_id=parent.downstream_circuit_id,
                    missing_inputs=parent_context.missing_inputs or ("upstream prospective fault current",),
                )
                progressed = True
                continue

            path_circuit_id = parent.downstream_circuit_id
            if not path_circuit_id:
                contexts[relationship.pair_key] = PairFaultContext(
                    pair_key=relationship.pair_key,
                    prospective_fault_current_ka=None,
                    basis="The intervening protected cable could not be identified from the hierarchy.",
                    path_circuit_id=None,
                    missing_inputs=("intervening protected cable identity",),
                )
                progressed = True
                continue

            path = cable_paths.get(path_circuit_id)
            if path is None:
                contexts[relationship.pair_key] = PairFaultContext(
                    pair_key=relationship.pair_key,
                    prospective_fault_current_ka=None,
                    basis=f"Fault propagation through {path_circuit_id} needs cable size, material, runs and length.",
                    path_circuit_id=path_circuit_id,
                    missing_inputs=(f"complete cable fault path for {path_circuit_id}",),
                )
                progressed = True
                continue

            estimate = propagate_three_phase_fault_screening(
                upstream_fault_current_ka=parent_context.prospective_fault_current_ka,
                line_to_line_voltage_v=graph.line_to_line_voltage_v,
                path=path,
            )
            contexts[relationship.pair_key] = PairFaultContext(
                pair_key=relationship.pair_key,
                prospective_fault_current_ka=estimate.prospective_fault_current_ka,
                basis=estimate.basis,
                path_circuit_id=path_circuit_id,
            )
            progressed = True

        if not progressed:
            for relationship in next_unresolved:
                contexts[relationship.pair_key] = PairFaultContext(
                    pair_key=relationship.pair_key,
                    prospective_fault_current_ka=None,
                    basis="Protection hierarchy could not be resolved into an upstream fault path.",
                    path_circuit_id=None,
                    missing_inputs=("resolvable upstream fault path",),
                )
            break
        unresolved = next_unresolved

    return tuple(contexts[item.pair_key] for item in relationships)
