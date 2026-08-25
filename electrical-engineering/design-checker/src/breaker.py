"""V0 breaker comparison.

This module performs a transparent numerical comparison between design current
Ib and selected breaker rated current In. It deliberately does not claim that
Ib <= In alone proves IEC compliance; the standards/rules layer will add the
applicable IEC 60364-4-43 requirements when verified source material is
available.
"""
from dataclasses import dataclass
from typing import Literal

Comparison = Literal["PASS", "FAIL"]

@dataclass(frozen=True)
class BreakerComparisonResult:
    ib_a: float
    in_a: float
    comparison: Comparison
    utilization: float
    headroom_a: float
    calculation_trace: tuple[str, ...]
    standards_status: str = "CALCULATED — NOT IEC VERIFIED"


def compare_breaker(*, ib_a: float, in_a: float) -> BreakerComparisonResult:
    if ib_a <= 0:
        raise ValueError("ib_a must be greater than 0")
    if in_a <= 0:
        raise ValueError("in_a must be greater than 0")

    passes = ib_a <= in_a
    utilization = ib_a / in_a
    headroom = in_a - ib_a
    comparison: Comparison = "PASS" if passes else "FAIL"
    trace = (
        f"Numerical check: Ib = {ib_a:.6f} A; In = {in_a:.6f} A",
        f"Ib <= In: {passes}",
        f"Breaker utilization = Ib / In = {utilization:.6f}",
        f"Breaker headroom = In - Ib = {headroom:.6f} A",
        "This is a numerical comparison only; it is not an IEC compliance verdict.",
    )
    return BreakerComparisonResult(ib_a, in_a, comparison, utilization, headroom, trace)
