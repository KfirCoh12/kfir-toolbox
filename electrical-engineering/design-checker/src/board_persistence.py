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


def board_autosave_path() -> Path:
    return _DEFAULT_PATH


def save_last_board(payload: dict, path: Path | None = None) -> Path:
    """Atomically persist the current Board Planner working state as JSON."""
    target = Path(path) if path is not None else board_autosave_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": _SCHEMA_VERSION, "board": payload}
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
    return payload


def clear_last_board(path: Path | None = None) -> None:
    """Remove the autosaved working board if it exists."""
    target = Path(path) if path is not None else board_autosave_path()
    try:
        target.unlink()
    except FileNotFoundError:
        pass
