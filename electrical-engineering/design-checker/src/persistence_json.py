"""Strict JSON helpers for engineering persistence boundaries.

Python's stdlib JSON encoder/decoder accepts NaN and Infinity by default even though
those tokens are not valid JSON. Its decoder also silently accepts duplicate object
keys by keeping only the final value. Persistence rejects both behaviors so ambiguous
or non-finite engineering state cannot be silently stored or reintroduced.
"""
from __future__ import annotations

import json
from typing import Any


def _reject_non_finite_constant(token: str) -> None:
    raise ValueError(f"Non-finite numeric token is not permitted in saved JSON: {token}")


def _reject_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"Duplicate object key is not permitted in saved JSON: {key}")
        document[key] = value
    return document


def dumps_strict(document: Any, **kwargs: Any) -> str:
    """Serialize standards-compliant JSON, rejecting NaN and infinities."""
    return json.dumps(document, allow_nan=False, **kwargs)


def loads_strict(text: str) -> Any:
    """Parse unambiguous standards-compliant JSON for persisted engineering state."""
    return json.loads(
        text,
        parse_constant=_reject_non_finite_constant,
        object_pairs_hook=_reject_duplicate_object_pairs,
    )
