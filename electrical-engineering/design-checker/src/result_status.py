"""User-facing feeder status summary derived from backend result objects.

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


def summarize_feeder_result(
    result: FeederResult,
    *,
    voltage_drop_requested: bool,
) -> FeederStatusSummary:
    """Create the UI-ready summary from the authoritative feeder result.

    Engineering status reflects implemented numerical checks only. Standards status
    remains incomplete whenever the feeder result has unresolved evidence/rules.
    """
    comparisons = [
        result.breaker.comparison if result.breaker else "NOT VERIFIED",
        result.ampacity_comparison.comparison,
    ]
    if voltage_drop_requested:
        comparisons.append(
            result.voltage_drop.comparison if result.voltage_drop else "NOT VERIFIED"
        )

    if "FAIL" in comparisons:
        engineering_status: EngineeringStatus = "FAIL"
    elif any(x in ("NOT VERIFIED", "NO LIMIT CHECKED") for x in comparisons):
        engineering_status = "INCOMPLETE"
    else:
        engineering_status = "PASS"

    standards_status: StandardsStatus = (
        "COMPLETE" if result.overall_outcome == "PASS" else "INCOMPLETE"
    )

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
    )
