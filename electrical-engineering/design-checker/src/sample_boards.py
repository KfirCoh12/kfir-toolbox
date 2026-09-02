"""Reusable realistic board fixtures for UI and workflow stress testing.

Fixtures are design-workflow examples, not standards templates. They deliberately
contain mixed single- and three-phase office loads so UI density, hierarchy,
phase balancing and unresolved engineering scope can all be exercised.
"""
from __future__ import annotations


def office_700m2_150_people_board() -> dict:
    """Return a busy office-board payload for the Board Planner/HMI sandbox.

    Design intent:
    - approximately 700 m² office
    - approximately 150 occupants
    - declared 400 A main feed for scenario context
    - mixed socket, lighting/AV, HVAC, pantry/utility and IT distribution

    The 400 A value is scenario metadata only; the calculation engine still
    derives its own load-sized incomer candidate from the branch demand.
    """
    branches: list[dict] = []
    uid_counter = 100

    def uid() -> str:
        nonlocal uid_counter
        uid_counter += 1
        return f"b{uid_counter}"

    def field(feeder_id: str, field_id: str, description: str) -> str:
        branch_uid = uid()
        branches.append(
            {
                "uid": branch_uid,
                "kind": "field",
                "parent_key": "root",
                "feeder_id": feeder_id,
                "field_id": field_id,
                "description": description,
                "material": "copper",
            }
        )
        return branch_uid

    def final(
        parent_key: str,
        circuit_id: str,
        description: str,
        load_kw: float,
        *,
        phase: str = "single",
        power_factor: float = 0.95,
        demand_factor: float = 1.0,
        phase_preference: str = "Auto",
    ) -> None:
        branches.append(
            {
                "uid": uid(),
                "kind": "final",
                "parent_key": parent_key,
                "circuit_id": circuit_id,
                "description": description,
                "mode": "auto",
                "load_kw": load_kw,
                "phase": phase,
                "power_factor": power_factor,
                "demand_factor": demand_factor,
                "material": "copper",
                "phase_preference": phase_preference,
                "connection_option_id": None,
            }
        )

    gp = field("F-GP", "FIELD-GP", "General power / workstation sockets")
    phases = ("L1", "L2", "L3")
    for index in range(15):
        final(
            gp,
            f"GP-{index + 1:02d}",
            f"Open-office socket zone {index + 1:02d}",
            3.6,
            phase="single",
            power_factor=0.95,
            demand_factor=0.65,
            phase_preference=phases[index % 3],
        )

    lighting = field("F-LTG", "FIELD-LTG", "Lighting, meeting rooms and AV")
    for index in range(6):
        final(
            lighting,
            f"LTG-{index + 1:02d}",
            f"Lighting zone {index + 1:02d}",
            2.5,
            phase="single",
            power_factor=0.95,
            demand_factor=0.90,
            phase_preference=phases[index % 3],
        )
    for index in range(3):
        final(
            lighting,
            f"AV-{index + 1:02d}",
            f"Meeting / AV power zone {index + 1:02d}",
            2.5,
            phase="single",
            power_factor=0.90,
            demand_factor=0.70,
            phase_preference=phases[index % 3],
        )

    hvac = field("F-HVAC", "FIELD-HVAC", "HVAC and ventilation")
    hvac_names = (
        "AHU office east",
        "AHU office west",
        "VRF outdoor unit A",
        "VRF outdoor unit B",
        "Fresh-air / extract plant",
        "Supplementary cooling plant",
    )
    for index, name in enumerate(hvac_names, start=1):
        final(
            hvac,
            f"HVAC-{index:02d}",
            name,
            18.0,
            phase="three",
            power_factor=0.90,
            demand_factor=0.90,
        )

    pantry = field("F-PAN", "FIELD-PAN", "Pantry, welfare and utility loads")
    final(pantry, "PAN-01", "Dishwasher", 9.0, phase="three", power_factor=0.90, demand_factor=0.80)
    final(pantry, "PAN-02", "Coffee / hot-drinks equipment", 12.0, phase="three", power_factor=0.95, demand_factor=0.80)
    final(pantry, "PAN-03", "Water heating", 9.0, phase="three", power_factor=0.95, demand_factor=0.80)
    final(pantry, "PAN-04", "Refrigeration and pantry sockets A", 3.0, phase="single", power_factor=0.90, demand_factor=0.80, phase_preference="L1")
    final(pantry, "PAN-05", "Refrigeration and pantry sockets B", 3.0, phase="single", power_factor=0.90, demand_factor=0.80, phase_preference="L2")
    final(pantry, "PAN-06", "Cleaning / utility sockets", 3.0, phase="single", power_factor=0.90, demand_factor=0.70, phase_preference="L3")

    it = field("F-IT", "FIELD-IT", "IT, communications and critical office loads")
    final(it, "IT-01", "Office UPS input", 20.0, phase="three", power_factor=0.95, demand_factor=0.85)
    final(it, "IT-02", "Server / network room cooling and power", 15.0, phase="three", power_factor=0.95, demand_factor=0.90)
    final(it, "IT-03", "Communications / security systems", 8.0, phase="three", power_factor=0.95, demand_factor=0.90)
    final(it, "IT-04", "Print / reprographics area", 8.0, phase="three", power_factor=0.90, demand_factor=0.70)

    return {
        "board_id": "OFFICE-DB-01",
        "description": "700 m² office · ~150 people · 400 A main feed",
        "line_to_line_voltage_v": 400.0,
        "line_to_neutral_voltage_v": 230.0,
        "declared_main_incomer_a": 400.0,
        "scenario_area_m2": 700.0,
        "scenario_people": 150,
        "scenario_note": "UI/workflow stress fixture; review and edit assumptions in the tool.",
        "selected_node": "busbar",
        "uid_counter": uid_counter,
        "branches": branches,
    }
