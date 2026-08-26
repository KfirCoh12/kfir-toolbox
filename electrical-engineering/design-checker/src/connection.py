"""V0.5 outlet / connection recommendation layer.

The catalogue provides conventional nominal connection ratings for workflow and
constraint solving. It deliberately does NOT claim product-specific or IEC
verification. Product family, poles, IP rating, interlocking and local/project
requirements must be verified separately before specification.
"""
from dataclasses import dataclass
from typing import Literal

Phase = Literal["single", "three"]

@dataclass(frozen=True)
class ConnectionOption:
    id: str
    label: str
    phase: Phase
    rating_a: float | None
    category: Literal["socket", "industrial_socket", "fixed_connection"]
    evidence_status: str
    note: str

_STATUS = "CONVENTIONAL RATING CATALOG — PRODUCT / STANDARD NOT VERIFIED"

CONNECTION_OPTIONS = (
    ConnectionOption("general_socket_16a_1ph", "General-purpose socket · 16 A", "single", 16.0, "socket", _STATUS, "Generic nominal rating only; national/product standard and socket type are not yet encoded."),
    ConnectionOption("industrial_16a_1ph", "Industrial plug/socket · 16 A · single-phase", "single", 16.0, "industrial_socket", _STATUS, "Generic industrial connection class; exact product configuration is not verified."),
    ConnectionOption("industrial_32a_1ph", "Industrial plug/socket · 32 A · single-phase", "single", 32.0, "industrial_socket", _STATUS, "Generic industrial connection class; exact product configuration is not verified."),
    ConnectionOption("industrial_63a_1ph", "Industrial plug/socket · 63 A · single-phase", "single", 63.0, "industrial_socket", _STATUS, "Generic industrial connection class; exact product configuration is not verified."),
    ConnectionOption("industrial_125a_1ph", "Industrial plug/socket · 125 A · single-phase", "single", 125.0, "industrial_socket", _STATUS, "Generic industrial connection class; exact product configuration is not verified."),
    ConnectionOption("industrial_16a_3ph", "Industrial plug/socket · 16 A · three-phase", "three", 16.0, "industrial_socket", _STATUS, "Generic industrial connection class; poles/neutral/earth arrangement is not yet selected."),
    ConnectionOption("industrial_32a_3ph", "Industrial plug/socket · 32 A · three-phase", "three", 32.0, "industrial_socket", _STATUS, "Generic industrial connection class; poles/neutral/earth arrangement is not yet selected."),
    ConnectionOption("industrial_63a_3ph", "Industrial plug/socket · 63 A · three-phase", "three", 63.0, "industrial_socket", _STATUS, "Generic industrial connection class; poles/neutral/earth arrangement is not yet selected."),
    ConnectionOption("industrial_125a_3ph", "Industrial plug/socket · 125 A · three-phase", "three", 125.0, "industrial_socket", _STATUS, "Generic industrial connection class; poles/neutral/earth arrangement is not yet selected."),
    ConnectionOption("fixed_connection_1ph", "Fixed connection / dedicated isolating arrangement", "single", None, "fixed_connection", _STATUS, "No generic current ceiling is assigned; equipment, terminals and isolation arrangement require project/product verification."),
    ConnectionOption("fixed_connection_3ph", "Fixed connection / dedicated isolating arrangement", "three", None, "fixed_connection", _STATUS, "No generic current ceiling is assigned; equipment, terminals and isolation arrangement require project/product verification."),
)

_BY_ID = {x.id: x for x in CONNECTION_OPTIONS}

def get_connection_option(option_id: str) -> ConnectionOption:
    try:
        return _BY_ID[option_id]
    except KeyError as exc:
        raise ValueError(f"Unknown connection option: {option_id}") from exc

def connection_options_for_phase(phase: Phase, *, include_fixed: bool = True) -> tuple[ConnectionOption, ...]:
    return tuple(x for x in CONNECTION_OPTIONS if x.phase == phase and (include_fixed or x.rating_a is not None))

def suggest_connection(*, phase: Phase, required_current_a: float) -> ConnectionOption:
    if required_current_a <= 0:
        raise ValueError("required_current_a must be greater than 0")
    rated = sorted((x for x in CONNECTION_OPTIONS if x.phase == phase and x.rating_a is not None), key=lambda x: x.rating_a)
    for option in rated:
        if option.rating_a >= required_current_a:
            return option
    return get_connection_option("fixed_connection_3ph" if phase == "three" else "fixed_connection_1ph")
