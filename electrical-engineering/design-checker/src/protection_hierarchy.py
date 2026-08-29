"""Protection topology derived from the electrical board graph.

This module provides the structural inputs needed by later protection-coordination
logic. It derives nearest upstream/downstream relationships and complete protection
chains strictly from graph ancestry. It does not evaluate selectivity, discrimination,
backup protection, fault current, trip curves, or standards compliance.
"""
from dataclasses import dataclass

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph


@dataclass(frozen=True)
class ProtectionRelationship:
    upstream_node_id: str
    downstream_node_id: str
    downstream_circuit_id: str | None
    upstream_rating_a: float | None = None
    downstream_rating_a: float | None = None


@dataclass(frozen=True)
class ProtectionChainDevice:
    node_id: str
    kind: str
    circuit_id: str | None
    board_ref: str | None
    rating_a: float | None


@dataclass(frozen=True)
class ProtectionChain:
    """Ordered protective path from the highest upstream device to one endpoint.

    Ratings are observations from the graph only. Their order or magnitude is not a
    selectivity result; manufacturer curves and fault-level data remain required for
    any coordination conclusion.
    """

    endpoint_node_id: str
    endpoint_circuit_id: str | None
    devices: tuple[ProtectionChainDevice, ...]

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(device.node_id for device in self.devices)

    @property
    def ratings_complete(self) -> bool:
        return all(device.rating_a is not None for device in self.devices)



def _is_protective(node: ElectricalNode) -> bool:
    return node.kind in ("incomer", "protective_device")


def _chain_device(node: ElectricalNode) -> ProtectionChainDevice:
    return ProtectionChainDevice(
        node_id=node.node_id,
        kind=node.kind,
        circuit_id=node.circuit_id,
        board_ref=node.board_ref,
        rating_a=node.rating_a,
    )


def protection_relationships(
    graph: BoardElectricalGraph,
) -> tuple[ProtectionRelationship, ...]:
    """Return each protective device paired with its nearest protective ancestor."""
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
            upstream_rating_a=upstream.rating_a,
            downstream_rating_a=node.rating_a,
        ))
    return tuple(relationships)


def protection_chain_for_node(
    graph: BoardElectricalGraph,
    node_id: str,
) -> ProtectionChain:
    """Return the complete protective ancestry ending at a protective graph node."""
    validate_board_graph(graph)
    node = graph.node_by_id.get(node_id)
    if node is None:
        raise ValueError(f"unknown node {node_id}")
    if not _is_protective(node):
        raise ValueError(f"node {node_id} is not a protective device")

    upstream = tuple(
        ancestor
        for ancestor in reversed(graph.ancestors_of(node.node_id))
        if _is_protective(ancestor)
    )
    devices = tuple(_chain_device(item) for item in upstream + (node,))
    return ProtectionChain(
        endpoint_node_id=node.node_id,
        endpoint_circuit_id=node.circuit_id,
        devices=devices,
    )


def protection_chains(
    graph: BoardElectricalGraph,
    *,
    terminal_only: bool = True,
) -> tuple[ProtectionChain, ...]:
    """Return ordered protection chains across the hierarchy.

    By default only terminal protective devices are returned: a device is terminal
    when it has no downstream protective descendant. This gives one end-to-end chain
    per protection branch and avoids returning every prefix of the same path. Set
    ``terminal_only=False`` when callers need a chain ending at every protective node.
    """
    validate_board_graph(graph)
    protective_nodes = tuple(node for node in graph.nodes if _is_protective(node))
    if terminal_only:
        protective_nodes = tuple(
            node
            for node in protective_nodes
            if not any(
                _is_protective(descendant)
                for descendant in graph.descendants_of(node.node_id)
            )
        )
    return tuple(
        protection_chain_for_node(graph, node.node_id)
        for node in protective_nodes
    )
