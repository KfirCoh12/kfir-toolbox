"""Shared runtime validation helpers for engineering inputs."""
from math import isfinite


def require_choice(name: str, value: str, allowed: tuple[str, ...]) -> None:
    """Reject unsupported string discriminators instead of silently falling through."""
    if value not in allowed:
        choices = ", ".join(repr(x) for x in allowed)
        raise ValueError(f"{name} must be one of: {choices}")


def require_positive_finite(name: str, value: float) -> None:
    """Require a finite numerical value strictly greater than zero."""
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value greater than 0")


def require_nonnegative_finite(name: str, value: float) -> None:
    """Require a finite numerical value greater than or equal to zero."""
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite value greater than or equal to 0")


def require_unit_interval(name: str, value: float) -> None:
    """Require a finite factor in the interval (0, 1]."""
    if not isfinite(value) or not 0 < value <= 1:
        raise ValueError(f"{name} must be a finite value greater than 0 and at most 1")
