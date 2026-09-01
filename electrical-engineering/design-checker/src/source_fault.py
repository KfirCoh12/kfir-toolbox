"""Narrow root-busbar prospective-fault-current model.

This module deliberately stops at the main board busbar. It can either carry a
reviewed declared fault level or calculate a transformer-terminal approximation from
nameplate kVA and impedance. It does not propagate fault current through downstream
cables and it is not an IEC 60909 short-circuit study.
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Literal

FaultSourceKind = Literal["DECLARED_BUSBAR", "TRANSFORMER_TERMINAL"]


@dataclass(frozen=True)
class FaultSourceDeclaration:
    kind: FaultSourceKind
    evidence_record_ref: str
    rule_basis_ref: str
    prospective_fault_current_ka: float | None = None
    transformer_rated_power_kva: float | None = None
    transformer_secondary_voltage_v: float | None = None
    transformer_impedance_percent: float | None = None


@dataclass(frozen=True)
class RootBusbarFaultResult:
    prospective_fault_current_ka: float
    evidence_record_ref: str
    rule_basis_ref: str
    basis: str
    source_kind: FaultSourceKind


def _positive(name: str, value: float | None) -> float:
    if value is None or not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value greater than 0")
    return float(value)


def _required_ref(name: str, value: str) -> str:
    clean = str(value).strip()
    if not clean:
        raise ValueError(f"{name} is required")
    return clean


def calculate_root_busbar_fault(
    declaration: FaultSourceDeclaration,
) -> RootBusbarFaultResult:
    """Return a traceable prospective 3-phase RMS fault current at the root busbar.

    ``DECLARED_BUSBAR`` carries a reviewed project value without recalculation.
    ``TRANSFORMER_TERMINAL`` uses the transformer-only approximation
    In = S/(sqrt(3)U), Ik = In*100/uk. Upstream network impedance, motors, parallel
    sources, voltage factors and downstream cable impedance are outside this result.
    """
    evidence_ref = _required_ref("evidence_record_ref", declaration.evidence_record_ref)
    rule_ref = _required_ref("rule_basis_ref", declaration.rule_basis_ref)

    if declaration.kind == "DECLARED_BUSBAR":
        fault_ka = _positive(
            "prospective_fault_current_ka",
            declaration.prospective_fault_current_ka,
        )
        return RootBusbarFaultResult(
            prospective_fault_current_ka=fault_ka,
            evidence_record_ref=evidence_ref,
            rule_basis_ref=rule_ref,
            source_kind=declaration.kind,
            basis=(
                f"Reviewed prospective fault current declared at the main board busbar: "
                f"{fault_ka:g} kA RMS. The value is carried from the referenced project "
                "record; this module does not recalculate its upstream network basis."
            ),
        )

    if declaration.kind != "TRANSFORMER_TERMINAL":
        raise ValueError("unsupported fault source kind")

    kva = _positive("transformer_rated_power_kva", declaration.transformer_rated_power_kva)
    voltage = _positive(
        "transformer_secondary_voltage_v",
        declaration.transformer_secondary_voltage_v,
    )
    impedance = _positive(
        "transformer_impedance_percent",
        declaration.transformer_impedance_percent,
    )
    rated_current_a = kva * 1000.0 / (sqrt(3.0) * voltage)
    fault_ka = rated_current_a * (100.0 / impedance) / 1000.0
    return RootBusbarFaultResult(
        prospective_fault_current_ka=fault_ka,
        evidence_record_ref=evidence_ref,
        rule_basis_ref=rule_ref,
        source_kind=declaration.kind,
        basis=(
            f"Transformer-terminal approximation: {kva:g} kVA, {voltage:g} V, "
            f"uk={impedance:g}% gives {fault_ka:.3f} kA RMS using "
            "In=S/(sqrt(3)U) and Ik=In*100/uk. Upstream source impedance is neglected; "
            "motor contribution, parallel sources, IEC 60909 voltage factors and "
            "downstream cable impedance are not included."
        ),
    )
