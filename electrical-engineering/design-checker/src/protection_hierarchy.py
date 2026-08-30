"""Protection topology derived from the electrical board graph.

This module provides structural inputs for protection-coordination logic. It derives
nearest upstream/downstream relationships and complete protection chains strictly from
graph ancestry. It can also attach conservative coordination status and structured
evidence readiness to each adjacent protective-device pair.

Observed breaker ratings are topology data only. Rating order is never treated as
proof of selectivity, discrimination, backup protection, breaking capacity, fault
protection, trip-curve performance, or standards compliance.
"""
from dataclasses import dataclass
from math import isclose
from typing import Mapping

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .protection import ProtectionCoordinationStatus
from .protection_evidence import (
    CoordinationEvidence,
    EvidenceReadiness,
    conservative_status_from_evidence,
    evidence_readiness,
)

ProtectionPairKey = tuple[str, str]


@dataclass(frozen=True)
class ProtectionRelationship:
    upstream_node_id: str
    downstream_node_id: str
    downstream_circuit_id: str | None
    upstream_rating_a: float | None = None
    downstream_rating_a: float | None = None

    @property
    def pair_key(self) -> ProtectionPairKey:
        return (self.upstream_node_id, self.downstream_node_id)


@dataclass(frozen=True)
class ProtectionCoordinationAssessment:
    """One adjacent protective-device pair with evidence-aware conservative status.

    The two ratings are observations from the hierarchy. They may be useful planning
    context, but their relative magnitude does not change ``coordination`` status.
    ``readiness`` describes only whether expected evidence categories are present; it
    is never itself a protection or selectivity verification result.
    """

    relationship: ProtectionRelationship
    evidence: CoordinationEvidence
    readiness: EvidenceReadiness
    coordination: ProtectionCoordinationStatus

    @property
    def upstream_rating_a(self) -> float | None:
        return self.relationship.upstream_rating_a

    @property
    def downstream_rating_a(self) -> float | None:
        return self.relationship.downstream_rating_a

    @property
    def missing_protection_evidence(self) -> tuple[str, ...]:
        return self.readiness.missing_protection_evidence

    @property
    def missing_selectivity_evidence(self) -> tuple[str, ...]:
        return self.readiness.missing_selectivity_evidence


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


def _assert_evidence_rating_consistency(
    relationship: ProtectionRelationship,
    evidence: CoordinationEvidence,
) -> None:
    """Fail if declared evidence contradicts an already-observed topology rating.

    A graph rating is not promoted into evidence automatically. This guard only
    prevents two explicit backend inputs from silently disagreeing.
    """
    comparisons = (
        (
            "upstream",
            relationship.upstream_rating_a,
            evidence.upstream_device.rating_a if evidence.upstream_device else None,
        ),
        (
            "downstream",
            relationship.downstream_rating_a,
            evidence.downstream_device.rating_a if evidence.downstream_device else None,
        ),
    )
    for side, topology_rating, evidence_rating in comparisons:
        if topology_rating is None or evidence_rating is None:
            continue
        if not isclose(float(topology_rating), float(evidence_rating), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                f"{side} evidence rating for {relationship.upstream_node_id} -> "
                f"{relationship.downstream_node_id} disagrees with topology rating"
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


def protection_coordination_assessments(
    graph: BoardElectricalGraph,
    *,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
    evidence_by_pair: Mapping[ProtectionPairKey, CoordinationEvidence] | None = None,
) -> tuple[ProtectionCoordinationAssessment, ...]:
    """Attach evidence-aware conservative status to each adjacent protection pair.

    Evidence is keyed by ``(upstream_node_id, downstream_node_id)`` so each pair can
    carry independent fault/device/cable/manufacturer inputs. Missing pairs receive an
    empty evidence bundle and therefore explicitly report what they still need.

    Supplying complete evidence only makes a pair ready for a future engineering
    check. It cannot produce ``VERIFIED`` here. Rating order is never evidence of
    selectivity, and graph ratings are never silently promoted into evidence.
    """
    relationships = protection_relationships(graph)
    supplied = dict(evidence_by_pair or {})
    known_keys = {relationship.pair_key for relationship in relationships}
    unknown_keys = sorted(set(supplied) - known_keys)
    if unknown_keys:
        formatted = ", ".join(f"{upstream} -> {downstream}" for upstream, downstream in unknown_keys)
        raise ValueError(f"evidence supplied for unknown protection relationship(s): {formatted}")

    assessments: list[ProtectionCoordinationAssessment] = []
    for relationship in relationships:
        evidence = supplied.get(relationship.pair_key, CoordinationEvidence())
        _assert_evidence_rating_consistency(relationship, evidence)
        readiness = evidence_readiness(evidence)
        coordination = conservative_status_from_evidence(
            evidence,
            protection_check_requested=protection_check_requested,
            selectivity_check_requested=selectivity_check_requested,
        )
        assessments.append(ProtectionCoordinationAssessment(
            relationship=relationship,
            evidence=evidence,
            readiness=readiness,
            coordination=coordination,
        ))
    return tuple(assessments)


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
