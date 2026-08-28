"""Protection hierarchy derived from the electrical board graph.

This module derives nearest upstream/downstream device relationships from topology
so later coordination logic does not require manual pairing in the UI.
"""
from dataclasses import dataclass

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph


@dataclass(frozen=True)
class ProtectionRelationship:
    upstream_node_id: str
    downstream_node_id: str
    downstream_circuit_id: str | None


def _is_protective(node: ElectricalNode) -> bool:
    return node.kind in ("incomer", "protective_device")


def protection_relationships(
    graph: BoardElectricalGraph,
) -> tuple[ProtectionRelationship, ...]:
    """Return each device paired with its nearest device ancestor."""
    validate_board_graph(graph)
    relationships: list[ProtectionRelationship] = []
    for node in graph.nodes:
        if not _is_protective(node):
            continue
        upstream = next(
            (ancestor for ancestor in graph.ancestors_of(node.node_id) if _is_protective(ancestor)),
            None,
        )
        if upstream is None:
            continue
        relationships.append(ProtectionRelationship(
            upstream_node_id=upstream.node_id,
            downstream_node_id=node.node_id,
            downstream_circuit_id=node.circuit_id,
        ))
    return tuple(relationships)
