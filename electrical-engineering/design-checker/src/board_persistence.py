"""Local persistence for the Board Planner working board.

The working copy is intentionally stored outside the repository so Git pulls and
checkouts do not overwrite it or accidentally commit project-specific board data.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

_SCHEMA_VERSION = 1
_DEFAULT_PATH = Path.home() / ".kfir-toolbox" / "board-planner" / "last_board.json"
_DEFAULT_LINE_TO_LINE_V = 400.0
_DEFAULT_LINE_TO_NEUTRAL_V = 230.0
_WIDGET_MINIMUM_SUPPLY = (1.0, 1.0)


def board_autosave_path() -> Path:
    return _DEFAULT_PATH


def _is_widget_minimum_supply(payload: dict) -> bool:
    try:
        return (
            float(payload.get("line_to_line_voltage_v")) == _WIDGET_MINIMUM_SUPPLY[0]
            and float(payload.get("line_to_neutral_voltage_v")) == _WIDGET_MINIMUM_SUPPLY[1]
        )
    except (TypeError, ValueError):
        return False


def _repair_legacy_widget_minimum_supply(payload: dict) -> dict:
    """Repair the known 1 V / 1 V Streamlit widget-initialization artifact.

    Board Planner historically used number inputs whose minimum value was 1 V. A
    widget-state reset could therefore replace the persisted 400/230 V defaults with
    1/1 V even though the user had not intentionally changed the supply. The exact
    paired minimum is treated as that legacy artifact; other user-entered voltages are
    preserved unchanged.
    """
    if not _is_widget_minimum_supply(payload):
        return payload
    repaired = dict(payload)
    repaired["line_to_line_voltage_v"] = _DEFAULT_LINE_TO_LINE_V
    repaired["line_to_neutral_voltage_v"] = _DEFAULT_LINE_TO_NEUTRAL_V
    return repaired


def _existing_board_payload(target: Path) -> dict | None:
    if not target.exists():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or document.get("schema_version") != _SCHEMA_VERSION:
        return None
    payload = document.get("board")
    return payload if isinstance(payload, dict) else None


def save_last_board(payload: dict, path: Path | None = None) -> Path:
    """Atomically persist the current Board Planner working state as JSON."""
    target = Path(path) if path is not None else board_autosave_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    board_payload = dict(payload)
    if _is_widget_minimum_supply(board_payload):
        existing = _existing_board_payload(target)
        if existing is not None and not _is_widget_minimum_supply(existing):
            previous_vll = existing.get("line_to_line_voltage_v")
            previous_vln = existing.get("line_to_neutral_voltage_v")
            if previous_vll is not None and previous_vln is not None:
                board_payload["line_to_line_voltage_v"] = previous_vll
                board_payload["line_to_neutral_voltage_v"] = previous_vln

    document = {"schema_version": _SCHEMA_VERSION, "board": board_payload}
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)

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


def load_last_board(path: Path | None = None) -> dict | None:
    """Load the autosaved working board, returning None when no save exists."""
    target = Path(path) if path is not None else board_autosave_path()
    if not target.exists():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read saved Board Planner state: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError("Saved Board Planner state must be a JSON object.")
    if document.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("Saved Board Planner state uses an unsupported schema version.")
    payload = document.get("board")
    if not isinstance(payload, dict):
        raise ValueError("Saved Board Planner state is missing its board object.")
    return _repair_legacy_widget_minimum_supply(payload)


def clear_last_board(path: Path | None = None) -> None:
    """Remove the autosaved working board if it exists."""
    target = Path(path) if path is not None else board_autosave_path()
    try:
        target.unlink()
    except FileNotFoundError:
        pass
