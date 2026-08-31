"""Apply decisive protection verifiers to actual hierarchy relationships.

This adapter keeps topology/evidence discovery separate from verification. Each result
is bound to one real upstream/downstream protective-device pair. Missing references or
inputs remain INSUFFICIENT DATA; a complete numeric breaking-capacity comparison may
produce VERIFIED or NOT VERIFIED for that narrow check only.
"""
from dataclasses import dataclass
from typing import Mapping

from .board_graph import BoardElectricalGraph
from .breaking_capacity_verifier import verify_breaking_capacity
from .protection_evidence import CoordinationEvidence
from .protection_hierarchy import (
    ProtectionPairKey,
    ProtectionRelationship,
    protection_relationships,
)
from .protection_verification import ProtectionVerificationResult, assert_result_matches_pair


@dataclass(frozen=True)
class PairBreakingCapacityVerification:
    relationship: ProtectionRelationship
    evidence: CoordinationEvidence
    result: ProtectionVerificationResult

    @property
    def pair_key(self) -> ProtectionPairKey:
        return self.relationship.pair_key


def _validate_known_keys(
    *,
    label: str,
    supplied_keys: set[ProtectionPairKey],
    known_keys: set[ProtectionPairKey],
) -> None:
    unknown = sorted(supplied_keys - known_keys)
    if unknown:
        formatted = ", ".join(f"{upstream} -> {downstream}" for upstream, downstream in unknown)
        raise ValueError(f"{label} supplied for unknown protection relationship(s): {formatted}")


def hierarchy_breaking_capacity_verifications(
    graph: BoardElectricalGraph,
    *,
    evidence_by_pair: Mapping[ProtectionPairKey, CoordinationEvidence] | None = None,
    requested_pairs: set[ProtectionPairKey] | None = None,
    rule_basis_ref_by_pair: Mapping[ProtectionPairKey, str] | None = None,
    evidence_record_ref_by_pair: Mapping[ProtectionPairKey, str] | None = None,
) -> tuple[PairBreakingCapacityVerification, ...]:
    """Run the narrow breaking-capacity verifier per real protection relationship.

    If ``requested_pairs`` is omitted, no pair is checked. This avoids silently turning
    available evidence into a verification request. References are pair-specific and
    never inherited from another relationship.
    """
    relationships = protection_relationships(graph)
    known_keys = {relationship.pair_key for relationship in relationships}
    evidence_map = dict(evidence_by_pair or {})
    request_set = set(requested_pairs or set())
    rule_refs = dict(rule_basis_ref_by_pair or {})
    record_refs = dict(evidence_record_ref_by_pair or {})

    _validate_known_keys(label="evidence", supplied_keys=set(evidence_map), known_keys=known_keys)
    _validate_known_keys(label="breaking-capacity request", supplied_keys=request_set, known_keys=known_keys)
    _validate_known_keys(label="rule-basis reference", supplied_keys=set(rule_refs), known_keys=known_keys)
    _validate_known_keys(label="evidence-record reference", supplied_keys=set(record_refs), known_keys=known_keys)

    output: list[PairBreakingCapacityVerification] = []
    for relationship in relationships:
        pair_key = relationship.pair_key
        evidence = evidence_map.get(pair_key, CoordinationEvidence())
        result = verify_breaking_capacity(
            upstream_node_id=relationship.upstream_node_id,
            downstream_node_id=relationship.downstream_node_id,
            evidence=evidence,
            requested=pair_key in request_set,
            rule_basis_ref=rule_refs.get(pair_key),
            evidence_record_ref=record_refs.get(pair_key),
        )
        assert_result_matches_pair(
            result,
            upstream_node_id=relationship.upstream_node_id,
            downstream_node_id=relationship.downstream_node_id,
        )
        output.append(PairBreakingCapacityVerification(
            relationship=relationship,
            evidence=evidence,
            result=result,
        ))
    return tuple(output)
