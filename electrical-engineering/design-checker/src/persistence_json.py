"""Strict JSON helpers for engineering persistence boundaries.

Python's stdlib JSON encoder/decoder accepts NaN and Infinity by default even though
those tokens are not valid JSON. Persistence must reject them so non-finite numeric
state cannot be silently stored or reintroduced into engineering inputs.
"""
from __future__ import annotations

import json
from typing import Any


def _reject_non_finite_constant(token: str) -> None:
    raise ValueError(f"Non-finite numeric token is not permitted in saved JSON: {token}")


def dumps_strict(document: Any, **kwargs: Any) -> str:
    """Serialize standards-compliant JSON, rejecting NaN and infinities."""
    return json.dumps(document, allow_nan=False, **kwargs)


def loads_strict(text: str) -> Any:
    """Parse JSON while rejecting Python's non-standard NaN/Infinity extensions."""
    return json.loads(text, parse_constant=_reject_non_finite_constant)
