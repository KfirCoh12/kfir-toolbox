"""V0.6 outlet / connection evidence and recommendation layer.

Industrial plug/socket nominal-rating classes are now tied to current IEC 60309
publication metadata. The evidence is intentionally scoped: it supports the IEC
60309 family and rating series used by this V0 catalogue, but does not by itself
verify an exact product, pole/contact arrangement, clock position, voltage/frequency
coding, IP degree, interlock, or national/project requirement.
"""
from dataclasses import dataclass
from typing import Literal

Phase = Literal["single", "three"]

@dataclass(frozen=True)
class EvidenceSource:
    standard: str
    edition: str
    publication_date: str
    title: str
    source_url: str
    scope_note: str

@dataclass(frozen=True)
class IEC60309Configuration:
    poles: str
    voltage_range_v: str
    frequency_hz: str
    clock_position_h: int
    identification_colour: str
    evidence_status: str
    evidence_sources: tuple[EvidenceSource, ...]

    @property
    def label(self) -> str:
        return f"{self.poles} · {self.voltage_range_v} · {self.frequency_hz} · {self.clock_position_h}h · {self.identification_colour}"

@dataclass(frozen=True)
class ConnectionOption:
    id: str
    label: str
    phase: Phase
    rating_a: float | None
    category: Literal["socket", "industrial_socket", "fixed_connection"]
    evidence_status: str
    note: str
    evidence_sources: tuple[EvidenceSource, ...] = ()

IEC_60309_1 = EvidenceSource(
    standard="IEC 60309-1:2021/COR1:2023",
    edition="5.0",
    publication_date="2021-06-18 (corrigendum 2023-05-17)",
    title="Plugs, fixed or portable socket-outlets and appliance inlets for industrial purposes - Part 1: General requirements",
    source_url="https://webstore.iec.ch/en/publication/59916",
    scope_note="Official IEC publication page confirms the current Part 1 edition and industrial-accessory scope up to 800 A.",
)

IEC_60309_2 = EvidenceSource(
    standard="IEC 60309-2:2021/COR1:2026",
    edition="5.0",
    publication_date="2021-06-18 (corrigendum 2026-08-19)",
    title="Plugs, fixed or portable socket-outlets and appliance inlets for industrial purposes - Part 2: Dimensional compatibility requirements for pin and contact-tube accessories",
    source_url="https://webstore.iec.ch/en/publication/59919",
    scope_note="Current corrected Part 2 applies to industrial accessories up to 125 A; public IEC preview material identifies the Series I 16 A, 32 A, 63 A and 125 A classes used here.",
)

IEC_60309_SOURCES = (IEC_60309_1, IEC_60309_2)


LEGRAND_400V_3PE = EvidenceSource(
    standard="Manufacturer product evidence — IEC 60309-1 / IEC 60309-2",
    edition="current product page",
    publication_date="accessed 2026-08-26",
    title="Legrand Hypra panel appliance inlet 380/415 V~ 16 A 3P+E",
    source_url="https://www.legrand.com/ecatalogue/en/catalog/products/panel-appliance-inlet-hypra-ip-44-380415-v-16-a-3pe-metal-052163",
    scope_note="Manufacturer page states conformity to IEC 60309-1/-2 and identifies 380/415 V 50/60 Hz, 3P+E, 4 poles, red, 6 h.",
)

LEGRAND_400V_3PNE = EvidenceSource(
    standard="Manufacturer product evidence — IEC 60309-1 / IEC 60309-2",
    edition="current product page",
    publication_date="accessed 2026-08-26",
    title="Legrand P17 panel socket 380/415 V~ 16 A 3P+N+E",
    source_url="https://www.legrand.com/ecatalogue/en/catalog/products/panel-mounting-socket-p17-ip6667-380415-v-16-3pne-555389",
    scope_note="Manufacturer page identifies 400 V 50/60 Hz, 3P+N+E, 5 poles, red, 6 h under EN/IEC 60309 product family.",
)

_CONFIG_STATUS = "IEC 60309 380/415 V CONFIGURATION EVIDENCE MAPPED — EXACT PRODUCT / IP / INTERLOCK NOT VERIFIED"

def iec60309_400v_configuration(*, requires_neutral: bool) -> IEC60309Configuration:
    return IEC60309Configuration(
        poles="3P+N+E" if requires_neutral else "3P+E",
        voltage_range_v="380/415 V AC",
        frequency_hz="50/60 Hz",
        clock_position_h=6,
        identification_colour="red",
        evidence_status=_CONFIG_STATUS,
        evidence_sources=IEC_60309_SOURCES + ((LEGRAND_400V_3PNE,) if requires_neutral else (LEGRAND_400V_3PE,)),
    )
_IEC_STATUS = "IEC 60309 FAMILY / RATING SERIES EVIDENCE MAPPED — EXACT CONFIGURATION / PRODUCT NOT VERIFIED"
_GENERIC_STATUS = "NATIONAL / PRODUCT STANDARD NOT VERIFIED"
_FIXED_STATUS = "PROJECT / PRODUCT-SPECIFIC CONNECTION — STANDARD BASIS NOT YET MAPPED"


def _industrial(option_id: str, rating: float, phase: Phase) -> ConnectionOption:
    phase_label = "single-phase" if phase == "single" else "three-phase"
    return ConnectionOption(
        option_id,
        f"IEC 60309 industrial plug/socket · {rating:g} A · {phase_label}",
        phase,
        rating,
        "industrial_socket",
        _IEC_STATUS,
        "The nominal rating class is mapped to IEC 60309 evidence. Exact poles/contacts, neutral/earth arrangement, voltage/frequency keying, clock position, IP degree, interlocking and product compliance still require selection/verification.",
        IEC_60309_SOURCES,
    )


CONNECTION_OPTIONS = (
    ConnectionOption(
        "general_socket_16a_1ph", "General-purpose socket · 16 A", "single", 16.0, "socket",
        _GENERIC_STATUS,
        "Generic nominal rating only; the applicable Israeli/national socket and product standard is not yet encoded.",
    ),
    _industrial("industrial_16a_1ph", 16.0, "single"),
    _industrial("industrial_32a_1ph", 32.0, "single"),
    _industrial("industrial_63a_1ph", 63.0, "single"),
    _industrial("industrial_125a_1ph", 125.0, "single"),
    _industrial("industrial_16a_3ph", 16.0, "three"),
    _industrial("industrial_32a_3ph", 32.0, "three"),
    _industrial("industrial_63a_3ph", 63.0, "three"),
    _industrial("industrial_125a_3ph", 125.0, "three"),
    ConnectionOption(
        "fixed_connection_1ph", "Fixed connection / dedicated isolating arrangement", "single", None, "fixed_connection",
        _FIXED_STATUS,
        "No generic current ceiling is assigned; equipment terminals, isolating means and project requirements require separate verification.",
    ),
    ConnectionOption(
        "fixed_connection_3ph", "Fixed connection / dedicated isolating arrangement", "three", None, "fixed_connection",
        _FIXED_STATUS,
        "No generic current ceiling is assigned; equipment terminals, isolating means and project requirements require separate verification.",
    ),
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
    # Automatic recommendations intentionally prefer the evidence-mapped industrial
    # series. The generic national 16 A socket is not auto-selected until its own
    # national/product evidence layer is mapped.
    rated = sorted(
        (x for x in CONNECTION_OPTIONS if x.phase == phase and x.category == "industrial_socket" and x.rating_a is not None),
        key=lambda x: x.rating_a,
    )
    for option in rated:
        if option.rating_a >= required_current_a:
            return option
    return get_connection_option("fixed_connection_3ph" if phase == "three" else "fixed_connection_1ph")
