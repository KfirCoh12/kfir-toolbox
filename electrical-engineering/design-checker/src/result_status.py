"""User-facing feeder status and result interpretation derived from backend result objects.

The UI should render these decisions, not recreate engineering or standards logic.
"""
from dataclasses import dataclass
from typing import Literal

from .feeder import FeederResult

EngineeringStatus = Literal["PASS", "FAIL", "INCOMPLETE"]
StandardsStatus = Literal["COMPLETE", "INCOMPLETE"]

_BLOCKER_MESSAGES = {
    "breaker protection rule/current IEC basis": (
        "Protection verification is incomplete because the current IEC 60364-4-43 basis has not yet been integrated."
    ),
    "breaker_in_a": "Breaker rating is required before the feeder can be fully checked.",
    "cable ampacity inputs": "Cable ampacity inputs are incomplete.",
    "cable ampacity standards/data basis": "Cable ampacity evidence is incomplete for the selected conditions.",
    "permitted voltage-drop limit/source": "Voltage drop was calculated, but no verified permitted limit/source was supplied.",
}

@dataclass(frozen=True)
class FeederStatusSummary:
    engineering_status: EngineeringStatus
    standards_status: StandardsStatus
    open_item_count: int
    primary_blocker: str | None
    primary_message: str | None
    breaker_detail: str
    cable_detail: str
    voltage_drop_detail: str | None

def _breaker_detail(result: FeederResult) -> str:
    b = result.breaker
    if b is None:
        return "Breaker not checked."
    if b.comparison == "PASS":
        return f"Ib {b.ib_a:.1f} A ≤ In {b.in_a:.1f} A · {b.headroom_a:.1f} A numerical headroom"
    deficit = abs(b.headroom_a)
    return f"Ib exceeds In by {deficit:.1f} A · revise the breaker selection or feeder design"

def _cable_detail(result: FeederResult) -> str:
    c = result.ampacity_comparison
    if c.comparison == "NOT VERIFIED" or c.iz_a is None:
        return "Cable capacity could not be verified for the selected construction/installation conditions."
    if c.comparison == "PASS":
        return f"Iz {c.iz_a:.1f} A ≥ Ib {c.ib_a:.1f} A · {c.headroom_a:.1f} A ampacity headroom"
    deficit = abs(c.headroom_a or 0.0)
    return f"Ib exceeds Iz by {deficit:.1f} A · increase cable capacity or revise the installation conditions"

def _voltage_drop_detail(result: FeederResult, requested: bool) -> str | None:
    if not requested:
        return None
    vd = result.voltage_drop
    if vd is None:
        return "Voltage-drop check is incomplete."
    actual = vd.voltage_drop_percent
    limit = vd.permitted_limit_percent
    if vd.comparison == "NO LIMIT CHECKED" or limit is None:
        return f"Calculated drop {actual:.2f}% · no verified permitted limit was checked"
    margin = limit - actual
    if vd.comparison == "PASS":
        return f"{actual:.2f}% ≤ {limit:.2f}% · {margin:.2f} percentage points remaining"
    return f"{actual:.2f}% > {limit:.2f}% · exceeds the permitted limit by {abs(margin):.2f} percentage points"

def summarize_feeder_result(
    result: FeederResult,
    *,
    voltage_drop_requested: bool,
) -> FeederStatusSummary:
    comparisons = [
        result.breaker.comparison if result.breaker else "NOT VERIFIED",
        result.ampacity_comparison.comparison,
    ]
    if voltage_drop_requested:
        comparisons.append(result.voltage_drop.comparison if result.voltage_drop else "NOT VERIFIED")

    if "FAIL" in comparisons:
        engineering_status: EngineeringStatus = "FAIL"
    elif any(x in ("NOT VERIFIED", "NO LIMIT CHECKED") for x in comparisons):
        engineering_status = "INCOMPLETE"
    else:
        engineering_status = "PASS"

    standards_status: StandardsStatus = "COMPLETE" if result.overall_outcome == "PASS" else "INCOMPLETE"
    blocker = result.missing_or_unverified[0] if result.missing_or_unverified else None
    if engineering_status == "FAIL":
        message = "One or more implemented engineering checks failed. Review the result cards and calculation details."
    elif blocker is not None:
        message = _BLOCKER_MESSAGES.get(blocker, f"Verification is incomplete: {blocker}.")
    else:
        message = None

    return FeederStatusSummary(
        engineering_status=engineering_status,
        standards_status=standards_status,
        open_item_count=len(result.missing_or_unverified),
        primary_blocker=blocker,
        primary_message=message,
        breaker_detail=_breaker_detail(result),
        cable_detail=_cable_detail(result),
        voltage_drop_detail=_voltage_drop_detail(result, voltage_drop_requested),
    )
