"""Versioned persistence for hierarchy-native electrical design inputs.

This module persists engineering inputs, not calculated results and not UI session state.
A saved project contains the shared electrical graph plus the explicit declarations that
change hierarchy calculation behavior. Calculated breaker/cable candidates and breaker
constraint assessments are rebuilt from those inputs when the project is loaded,
avoiding stale engineering results.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph
from .circuit_engine import CircuitDesignRequest
from .hierarchy_constraints import BreakerRatingConstraint, assess_breaker_constraints
from .hierarchy_planner import (
    FeederInstallationDeclaration,
    FeederPhaseMappingDeclaration,
    calculate_board_hierarchy,
)

_SCHEMA_VERSION = 2
_LEGACY_SCHEMA_VERSION = 1
_DEFAULT_PATH = Path.home() / ".kfir-toolbox" / "design-checker" / "last_hierarchy.json"


@dataclass(frozen=True)
class HierarchyEngineeringProject:
    """Persistable source-of-truth inputs for one hierarchy calculation."""

    graph: BoardElectricalGraph
    circuit_request_overrides: tuple[CircuitDesignRequest, ...] = tuple()
    feeder_installations: tuple[FeederInstallationDeclaration, ...] = tuple()
    feeder_phase_mappings: tuple[FeederPhaseMappingDeclaration, ...] = tuple()
    breaker_constraints: tuple[BreakerRatingConstraint, ...] = tuple()


def hierarchy_autosave_path() -> Path:
    return _DEFAULT_PATH


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array")
    return value


def _strict_dataclass(cls, raw: Any, label: str, *, tuple_fields: tuple[str, ...] = tuple()):
    data = _require_object(raw, label)
    allowed = {field.name for field in fields(cls)}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {', '.join(sorted(unknown))}")
    converted = dict(data)
    for name in tuple_fields:
        if name in converted:
            converted[name] = tuple(_require_list(converted[name], f"{label}.{name}"))
    try:
        return cls(**converted)
    except TypeError as exc:
        raise ValueError(f"{label} is missing required fields or has invalid structure: {exc}") from exc


def _node_to_dict(node: ElectricalNode) -> dict[str, Any]:
    data = asdict(node)
    data["issue_codes"] = list(node.issue_codes)
    return data


def _graph_to_dict(graph: BoardElectricalGraph) -> dict[str, Any]:
    return {
        "board_id": graph.board_id,
        "description": graph.description,
        "line_to_line_voltage_v": graph.line_to_line_voltage_v,
        "line_to_neutral_voltage_v": graph.line_to_neutral_voltage_v,
        "nodes": [_node_to_dict(node) for node in graph.nodes],
    }


def _graph_from_dict(raw: Any) -> BoardElectricalGraph:
    data = _require_object(raw, "project.graph")
    allowed = {
        "board_id",
        "description",
        "line_to_line_voltage_v",
        "line_to_neutral_voltage_v",
        "nodes",
    }
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(
            f"project.graph contains unknown fields: {', '.join(sorted(unknown))}"
        )
    missing = allowed - set(data)
    if missing:
        raise ValueError(
            f"project.graph is missing required fields: {', '.join(sorted(missing))}"
        )
    nodes = tuple(
        _strict_dataclass(
            ElectricalNode,
            node,
            f"project.graph.nodes[{index}]",
            tuple_fields=("issue_codes",),
        )
        for index, node in enumerate(_require_list(data["nodes"], "project.graph.nodes"))
    )
    graph = BoardElectricalGraph(
        board_id=data["board_id"],
        description=data["description"],
        line_to_line_voltage_v=data["line_to_line_voltage_v"],
        line_to_neutral_voltage_v=data["line_to_neutral_voltage_v"],
        nodes=nodes,
    )
    validate_board_graph(graph)
    return graph


def validate_hierarchy_project(project: HierarchyEngineeringProject) -> None:
    """Reject source inputs that cannot form one coherent hierarchy calculation.

    Persistence is a source-of-truth boundary, so validation includes declaration
    semantics and graph cross-references rather than only JSON/dataclass shape. The
    hierarchy calculation and constraint assessments are intentionally discarded;
    their role here is to exercise the same authoritative backend validation paths
    used by normal calculations.
    """
    if not isinstance(project, HierarchyEngineeringProject):
        raise ValueError("hierarchy project must be a HierarchyEngineeringProject")
    hierarchy = calculate_board_hierarchy(
        project.graph,
        project.circuit_request_overrides,
        project.feeder_installations,
        project.feeder_phase_mappings,
    )
    assess_breaker_constraints(project.graph, hierarchy, project.breaker_constraints)


def project_to_document(project: HierarchyEngineeringProject) -> dict[str, Any]:
    """Convert source inputs to the stable versioned JSON document contract."""
    validate_hierarchy_project(project)
    return {
        "schema_version": _SCHEMA_VERSION,
        "project": {
            "graph": _graph_to_dict(project.graph),
            "circuit_request_overrides": [asdict(item) for item in project.circuit_request_overrides],
            "feeder_installations": [asdict(item) for item in project.feeder_installations],
            "feeder_phase_mappings": [asdict(item) for item in project.feeder_phase_mappings],
            "breaker_constraints": [asdict(item) for item in project.breaker_constraints],
        },
    }


def project_from_document(document: Any) -> HierarchyEngineeringProject:
    """Decode a versioned document, rejecting silent schema or semantic drift.

    Version-1 documents are migrated explicitly by treating breaker constraints as an
    empty tuple because that schema predates persistence of those source inputs. New
    documents always use version 2.
    """
    root = _require_object(document, "saved hierarchy")
    unknown_root = set(root) - {"schema_version", "project"}
    if unknown_root:
        raise ValueError(
            f"saved hierarchy contains unknown fields: {', '.join(sorted(unknown_root))}"
        )
    schema_version = root.get("schema_version")
    if schema_version not in (_LEGACY_SCHEMA_VERSION, _SCHEMA_VERSION):
        raise ValueError("saved hierarchy uses an unsupported schema version")
    payload = _require_object(root.get("project"), "project")
    legacy_allowed = {
        "graph",
        "circuit_request_overrides",
        "feeder_installations",
        "feeder_phase_mappings",
    }
    allowed = legacy_allowed | {"breaker_constraints"}
    expected = legacy_allowed if schema_version == _LEGACY_SCHEMA_VERSION else allowed
    unknown = set(payload) - expected
    if unknown:
        raise ValueError(f"project contains unknown fields: {', '.join(sorted(unknown))}")
    missing = expected - set(payload)
    if missing:
        raise ValueError(f"project is missing required fields: {', '.join(sorted(missing))}")

    project = HierarchyEngineeringProject(
        graph=_graph_from_dict(payload["graph"]),
        circuit_request_overrides=tuple(
            _strict_dataclass(CircuitDesignRequest, item, f"project.circuit_request_overrides[{i}]")
            for i, item in enumerate(
                _require_list(payload["circuit_request_overrides"], "project.circuit_request_overrides")
            )
        ),
        feeder_installations=tuple(
            _strict_dataclass(FeederInstallationDeclaration, item, f"project.feeder_installations[{i}]")
            for i, item in enumerate(
                _require_list(payload["feeder_installations"], "project.feeder_installations")
            )
        ),
        feeder_phase_mappings=tuple(
            _strict_dataclass(FeederPhaseMappingDeclaration, item, f"project.feeder_phase_mappings[{i}]")
            for i, item in enumerate(
                _require_list(payload["feeder_phase_mappings"], "project.feeder_phase_mappings")
            )
        ),
        breaker_constraints=tuple(
            _strict_dataclass(BreakerRatingConstraint, item, f"project.breaker_constraints[{i}]")
            for i, item in enumerate(
                _require_list(payload.get("breaker_constraints", []), "project.breaker_constraints")
            )
        ),
    )
    validate_hierarchy_project(project)
    return project


def save_hierarchy_project(
    project: HierarchyEngineeringProject,
    path: Path | None = None,
) -> Path:
    """Atomically persist hierarchy engineering inputs as UTF-8 JSON."""
    target = Path(path) if path is not None else hierarchy_autosave_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(project_to_document(project), ensure_ascii=False, indent=2, sort_keys=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text)
        handle.flush()
    temp_path.replace(target)
    return target


def load_hierarchy_project(path: Path | None = None) -> HierarchyEngineeringProject | None:
    """Load hierarchy engineering inputs, returning None when no save exists."""
    target = Path(path) if path is not None else hierarchy_autosave_path()
    if not target.exists():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read saved hierarchy state: {exc}") from exc
    return project_from_document(document)


def clear_hierarchy_project(path: Path | None = None) -> None:
    target = Path(path) if path is not None else hierarchy_autosave_path()
    try:
        target.unlink()
    except FileNotFoundError:
        pass
