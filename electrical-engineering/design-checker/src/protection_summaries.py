"""Renderer-neutral protection summaries for future UI/reporting layers.

A summary deliberately keeps broad protection/selectivity status separate from the
narrow breaking-capacity verifier. A VERIFIED breaking-capacity comparison therefore
never promotes overall protection or selectivity to VERIFIED.
"""
from dataclasses import dataclass
from typing import Mapping

from .board_graph import BoardElectricalGraph
from .protection import VerificationStatus
from .protection_evidence import CoordinationEvidence
from .protection_hierarchy import (
    ProtectionPairKey,
    protection_coordination_assessments,
)
from .protection_verification_hierarchy import hierarchy_breaking_capacity_verifications


@dataclass(frozen=True)
class ProtectionPairSummary:
    upstream_node_id: str
    downstream_node_id: str
    downstream_circuit_id: str | None
    upstream_rating_a: float | None
    downstream_rating_a: float | None
    protection_status: VerificationStatus
    selectivity_status: VerificationStatus
    breaking_capacity_status: VerificationStatus
    missing_protection_evidence: tuple[str, ...]
    missing_selectivity_evidence: tuple[str, ...]
    breaking_capacity_missing_evidence: tuple[str, ...]
    breaking_capacity_basis: str
    breaking_capacity_rule_basis_ref: str | None
    breaking_capacity_verifier: str | None
    breaking_capacity_verifier_version: str | None

    @property
    def pair_key(self) -> ProtectionPairKey:
        return (self.upstream_node_id, self.downstream_node_id)


def protection_pair_summaries(
    graph: BoardElectricalGraph,
    *,
    evidence_by_pair: Mapping[ProtectionPairKey, CoordinationEvidence] | None = None,
    protection_check_requested: bool = False,
    selectivity_check_requested: bool = False,
    breaking_capacity_requested_pairs: set[ProtectionPairKey] | None = None,
    breaking_capacity_rule_basis_ref_by_pair: Mapping[ProtectionPairKey, str] | None = None,
    breaking_capacity_evidence_record_ref_by_pair: Mapping[ProtectionPairKey, str] | None = None,
) -> tuple[ProtectionPairSummary, ...]:
    """Build UI-safe summaries without collapsing independent engineering verdicts."""
    coordination = protection_coordination_assessments(
        graph,
        protection_check_requested=protection_check_requested,
        selectivity_check_requested=selectivity_check_requested,
        evidence_by_pair=evidence_by_pair,
    )
    breaking_capacity = hierarchy_breaking_capacity_verifications(
        graph,
        evidence_by_pair=evidence_by_pair,
        requested_pairs=breaking_capacity_requested_pairs,
        rule_basis_ref_by_pair=breaking_capacity_rule_basis_ref_by_pair,
        evidence_record_ref_by_pair=breaking_capacity_evidence_record_ref_by_pair,
    )

    capacity_by_pair = {item.pair_key: item for item in breaking_capacity}
    summaries: list[ProtectionPairSummary] = []
    for assessment in coordination:
        pair_key = assessment.relationship.pair_key
        capacity = capacity_by_pair.get(pair_key)
        if capacity is None:
            raise ValueError(f"missing breaking-capacity result for protection pair {pair_key}")
        result = capacity.result
        provenance = result.provenance
        summaries.append(ProtectionPairSummary(
            upstream_node_id=assessment.relationship.upstream_node_id,
            downstream_node_id=assessment.relationship.downstream_node_id,
            downstream_circuit_id=assessment.relationship.downstream_circuit_id,
            upstream_rating_a=assessment.relationship.upstream_rating_a,
            downstream_rating_a=assessment.relationship.downstream_rating_a,
            protection_status=assessment.coordination.protection_status,
            selectivity_status=assessment.coordination.selectivity_status,
            breaking_capacity_status=result.status,
            missing_protection_evidence=assessment.missing_protection_evidence,
            missing_selectivity_evidence=assessment.missing_selectivity_evidence,
            breaking_capacity_missing_evidence=result.missing_evidence,
            breaking_capacity_basis=result.basis,
            breaking_capacity_rule_basis_ref=(
                provenance.rule_basis_ref if provenance is not None else None
            ),
            breaking_capacity_verifier=(
                provenance.verifier.name if provenance is not None else None
            ),
            breaking_capacity_verifier_version=(
                provenance.verifier.version if provenance is not None else None
            ),
        ))
    return tuple(summaries)
