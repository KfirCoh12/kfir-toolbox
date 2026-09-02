"""Persistence for the Board Planner working board.

Local use defaults to storage outside the repository so Git pulls and checkouts do
not overwrite it or accidentally commit project-specific board data. Hosted
instances can point the same persistence layer at a private mounted data directory
through ``KFIR_TOOLBOX_DATA_DIR`` without changing application code.

Private hosted sessions may additionally enter ``persistence_scope_for_email``.
That scope stores board data below an opaque per-user directory so authenticated
users cannot overwrite one another's working boards. The email itself is never
written into the filesystem path.

The saved board is also shared by adjacent engineering pages. Callers may therefore
write only the fields they own; existing top-level project metadata is preserved
unless the caller explicitly replaces that key. This prevents Board Planner autosave
from deleting protection/fault-study data written by another page.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from tempfile import NamedTemporaryFile

from .persistence_json import dumps_strict, loads_strict

_SCHEMA_VERSION = 1
_DATA_DIR_ENV = "KFIR_TOOLBOX_DATA_DIR"
_LOCAL_DATA_ROOT = Path.home() / ".kfir-toolbox"
_DEFAULT_LINE_TO_LINE_V = 400.0
_DEFAULT_LINE_TO_NEUTRAL_V = 230.0
_WIDGET_MINIMUM_SUPPLY = (1.0, 1.0)
_CURRENT_USER_STORAGE_KEY: ContextVar[str | None] = ContextVar(
    "kfir_toolbox_user_storage_key",
    default=None,
)


def toolbox_data_root() -> Path:
    """Return the private writable data root for local or hosted operation.

    When ``KFIR_TOOLBOX_DATA_DIR`` is unset, existing local installations keep
    using ``~/.kfir-toolbox``. A hosted deployment can set the variable to a
    persistent private volume such as ``/var/lib/kfir-toolbox``.
    """
    configured = os.environ.get(_DATA_DIR_ENV)
    if configured is None or not configured.strip():
        return _LOCAL_DATA_ROOT
    return Path(configured).expanduser()


def storage_key_for_email(email: str) -> str:
    """Return a deterministic opaque storage key for an authenticated email."""
    normalized = str(email).strip().lower()
    if not normalized:
        raise ValueError("Authenticated email is required for user-scoped persistence.")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"user-{digest}"


@contextmanager
def persistence_scope_for_email(email: str) -> Iterator[str]:
    """Scope persistence to one authenticated user for the current execution context.

    ContextVar keeps the identity local to the current Streamlit execution context
    instead of mutating process-wide environment variables, which would be unsafe
    when multiple users are served by the same Python process.
    """
    storage_key = storage_key_for_email(email)
    token = _CURRENT_USER_STORAGE_KEY.set(storage_key)
    try:
        yield storage_key
    finally:
        _CURRENT_USER_STORAGE_KEY.reset(token)


def board_autosave_path() -> Path:
    root = toolbox_data_root()
    storage_key = _CURRENT_USER_STORAGE_KEY.get()
    if storage_key is not None:
        root = root / "users" / storage_key
    return root / "board-planner" / "last_board.json"


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
        document = loads_strict(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) or document.get("schema_version") != _SCHEMA_VERSION:
        return None
    payload = document.get("board")
    return payload if isinstance(payload, dict) else None


def _merge_existing_board_payload(existing: dict | None, payload: dict) -> dict:
    """Merge a caller-owned board update with existing shared project metadata.

    Explicit keys in ``payload`` always win, including explicit ``None`` or empty
    values. Keys omitted by the caller are retained from the existing board. This
    lets Board Planner update its live structural fields without deleting protection
    data maintained by Protection Checks.
    """
    merged = dict(existing or {})
    merged.update(payload)
    return merged


def _fsync_directory(directory: Path) -> None:
    """Persist directory metadata where the host platform supports directory fsync."""
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def save_last_board(payload: dict, path: Path | None = None) -> Path:
    """Durably persist a board update while retaining other pages' top-level data.

    The board autosave is a shared project record. Callers may submit the fields they
    own; omitted existing top-level fields are retained, while explicitly supplied
    keys replace the previous value.
    """
    target = Path(path) if path is not None else board_autosave_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    existing = _existing_board_payload(target)
    board_payload = _merge_existing_board_payload(existing, dict(payload))
    if _is_widget_minimum_supply(board_payload):
        if existing is not None and not _is_widget_minimum_supply(existing):
            previous_vll = existing.get("line_to_line_voltage_v")
            previous_vln = existing.get("line_to_neutral_voltage_v")
            if previous_vll is not None and previous_vln is not None:
                board_payload["line_to_line_voltage_v"] = previous_vll
                board_payload["line_to_neutral_voltage_v"] = previous_vln

    document = {"schema_version": _SCHEMA_VERSION, "board": board_payload}
    text = dumps_strict(document, ensure_ascii=False, indent=2, sort_keys=True)
    temp_path: Path | None = None
    try:
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
            os.fsync(handle.fileno())
        temp_path.replace(target)
        temp_path = None
        _fsync_directory(target.parent)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
    return target


def load_last_board(path: Path | None = None) -> dict | None:
    """Load the autosaved working board, returning None when no save exists."""
    target = Path(path) if path is not None else board_autosave_path()
    if not target.exists():
        return None
    try:
        document = loads_strict(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
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
        return
    _fsync_directory(target.parent)
