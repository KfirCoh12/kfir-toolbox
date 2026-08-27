"""First interactive board-planning UI over the shared circuit engine."""
import pandas as pd
import streamlit as st

from src.board_planner import (
    BoardPhasePreference,
    BoardPlanRequest,
    calculate_board_plan,
)
from src.circuit_engine import CircuitDesignRequest

st.set_page_config(
    page_title="Board Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {max-width: 1380px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 0.8rem 0 1rem 0;}
.hero h1 {margin:0; font-size:2.35rem; letter-spacing:-0.03em;}
.hero p {margin:.55rem 0 0 0; color:#94a3b8; font-size:1rem;}
.eyebrow {font-size:.76rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.4rem;}
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {border-radius:10px !important;}
[data-testid="stNumberInput"],
[data-testid="stSelectbox"],
[data-testid="stTextInput"] {max-width:280px;}
div.stButton > button {min-height:3rem; border-radius:12px; font-weight:700;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px; background:#111827; border-color:#263449;}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1.15rem 1.25rem;}
[data-testid="stMetric"] {
    background:#111827;
    border:1px solid #263449;
    border-radius:14px;
    padding:1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="hero"><div class="eyebrow">Electrical engineering · Board planning preview</div><h1>⚡ Board Planner</h1><p>Add consumers, run the shared circuit calculations, and see a provisional phase plan and incomer candidate.</p></div>""",
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.caption("BOARD → CIRCUITS → PHASE ALLOCATION → PROVISIONAL INCOMER")
    st.markdown("#### Board")
    board_id_col, description_col, _ = st.columns([1, 2, 1])
    with board_id_col:
        board_id = st.text_input("Board ID", value="DB-01")
    with description_col:
        description = st.text_input("Description", value="Distribution board")

    with st.expander("Board supply"):
        voltage_ll_col, voltage_ln_col, _ = st.columns([1, 1, 2])
        with voltage_ll_col:
            voltage_ll = st.number_input(
                "Line-line voltage (V)", min_value=1.0, value=400.0, step=5.0
            )
        with voltage_ln_col:
            voltage_ln = st.number_input(
                "Line-neutral voltage (V)", min_value=1.0, value=230.0, step=5.0
            )

    st.markdown("#### Consumers")
    st.caption("Add or remove rows directly. Phase lock is optional for single-phase circuits.")

    seed = pd.DataFrame(
        [
            {
                "Circuit": "C-01",
                "Description": "Lighting",
                "Load kW": 2.0,
                "Phase": "Single-phase",
                "Power factor": 0.90,
                "Demand factor": 1.00,
                "Material": "Copper",
                "Phase lock": "Auto",
            },
            {
                "Circuit": "C-02",
                "Description": "Sockets",
                "Load kW": 3.0,
                "Phase": "Single-phase",
                "Power factor": 0.90,
                "Demand factor": 0.80,
                "Material": "Copper",
                "Phase lock": "Auto",
            },
            {
                "Circuit": "C-03",
                "Description": "Three-phase load",
                "Load kW": 12.0,
                "Phase": "Three-phase",
                "Power factor": 0.90,
                "Demand factor": 1.00,
                "Material": "Copper",
                "Phase lock": "Auto",
            },
        ]
    )
    if "board_editor_seed" not in st.session_state:
        st.session_state["board_editor_seed"] = seed

    edited = st.data_editor(
        st.session_state["board_editor_seed"],
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "Circuit": st.column_config.TextColumn("Circuit", required=True, width="small"),
            "Description": st.column_config.TextColumn("Description", required=True, width="medium"),
            "Load kW": st.column_config.NumberColumn(
                "Load kW", min_value=0.1, step=0.5, format="%.1f", required=True
            ),
            "Phase": st.column_config.SelectboxColumn(
                "Phase", options=["Single-phase", "Three-phase"], required=True
            ),
            "Power factor": st.column_config.NumberColumn(
                "PF", min_value=0.01, max_value=1.0, step=0.01, format="%.2f", required=True
            ),
            "Demand factor": st.column_config.NumberColumn(
                "Demand", min_value=0.01, max_value=1.0, step=0.05, format="%.2f", required=True
            ),
            "Material": st.column_config.SelectboxColumn(
                "Material", options=["Copper", "Aluminium"], required=True
            ),
            "Phase lock": st.column_config.SelectboxColumn(
                "Phase lock", options=["Auto", "L1", "L2", "L3"], required=True
            ),
        },
        key="board_circuit_editor",
    )

records = edited.to_dict("records")
board_signature = (
    board_id.strip(),
    description.strip(),
    float(voltage_ll),
    float(voltage_ln),
    tuple(
        (
            str(row.get("Circuit", "")).strip(),
            str(row.get("Description", "")).strip(),
            float(row.get("Load kW", 0) or 0),
            str(row.get("Phase", "")),
            float(row.get("Power factor", 0) or 0),
            float(row.get("Demand factor", 0) or 0),
            str(row.get("Material", "")),
            str(row.get("Phase lock", "Auto")),
        )
        for row in records
    ),
)

plan_board = st.button("Plan board", type="primary", use_container_width=True)

if plan_board:
    try:
        if not records:
            raise ValueError("Add at least one consumer before planning the board.")

        circuits = []
        preferences = []
        for row_number, row in enumerate(records, start=1):
            circuit_id = str(row.get("Circuit", "")).strip()
            circuit_description = str(row.get("Description", "")).strip()
            if not circuit_id:
                raise ValueError(f"Row {row_number}: Circuit is required.")
            if not circuit_description:
                raise ValueError(f"Row {row_number}: Description is required.")

            phase_label = str(row.get("Phase", ""))
            phase = "three" if phase_label == "Three-phase" else "single"
            phase_lock = str(row.get("Phase lock", "Auto"))
            if phase == "three" and phase_lock != "Auto":
                raise ValueError(
                    f"{circuit_id}: phase lock only applies to single-phase circuits."
                )

            load_kw = float(row.get("Load kW", 0) or 0)
            power_factor = float(row.get("Power factor", 0) or 0)
            demand_factor = float(row.get("Demand factor", 0) or 0)
            if load_kw <= 0:
                raise ValueError(f"{circuit_id}: Load kW must be greater than 0.")
            if not 0 < power_factor <= 1:
                raise ValueError(f"{circuit_id}: Power factor must be greater than 0 and at most 1.")
            if not 0 < demand_factor <= 1:
                raise ValueError(f"{circuit_id}: Demand factor must be greater than 0 and at most 1.")

            material = "aluminium" if str(row.get("Material", "")) == "Aluminium" else "copper"
            circuits.append(
                CircuitDesignRequest(
                    circuit_id=circuit_id,
                    description=circuit_description,
                    load_type="kw",
                    load_value=load_kw,
                    voltage_v=float(voltage_ll if phase == "three" else voltage_ln),
                    phase=phase,
                    power_factor=power_factor,
                    demand_factor=demand_factor,
                    material=material,
                )
            )
            if phase == "single" and phase_lock in ("L1", "L2", "L3"):
                preferences.append(
                    BoardPhasePreference(circuit_id=circuit_id, phase=phase_lock)
                )

        result = calculate_board_plan(
            BoardPlanRequest(
                board_id=board_id,
                description=description,
                circuits=tuple(circuits),
                line_to_line_voltage_v=float(voltage_ll),
                line_to_neutral_voltage_v=float(voltage_ln),
                phase_preferences=tuple(preferences),
            )
        )
        st.session_state["board_plan_result"] = {
            "signature": board_signature,
            "result": result,
        }
    except (TypeError, ValueError) as exc:
        st.session_state.pop("board_plan_result", None)
        st.error(str(exc))

stored = st.session_state.get("board_plan_result")
if stored and stored["signature"] != board_signature:
    st.session_state.pop("board_plan_result", None)
    stored = None

if stored:
    result = stored["result"]

    if result.scope_status == "SUPPORTED_SCOPE":
        st.success("Board circuits were planned inside the currently supported circuit scope.")
    elif result.scope_status == "PARTIAL_SCOPE":
        st.warning(
            "The board plan contains usable numerical results, but one or more circuit checks remain outside the supported scope."
        )
    else:
        st.warning("One or more board circuits could not be verified from the supported data.")

    incomer = result.incomer_candidate
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(
        "Incomer candidate",
        f"{incomer.breaker_rating_a:.0f} A" if incomer.breaker_rating_a is not None else "—",
    )
    m2.metric("L1 planned current", f"{result.phase_balance.l1_current_a:.1f} A")
    m3.metric("L2 planned current", f"{result.phase_balance.l2_current_a:.1f} A")
    m4.metric("L3 planned current", f"{result.phase_balance.l3_current_a:.1f} A")
    m5.metric("Phase spread", f"{result.phase_balance.spread_a:.1f} A")

    st.markdown("### Circuit schedule")
    schedule = []
    for row in result.schedule_rows:
        cable = "—"
        if row.cable_mm2 is not None:
            cable = (
                f"{row.cable_runs} × {row.cable_mm2:g} mm²"
                if (row.cable_runs or 1) > 1
                else f"{row.cable_mm2:g} mm²"
            )
        connection = "—"
        circuit_result = next(
            c for c in result.circuits if c.request.circuit_id == row.circuit_id
        )
        if circuit_result.selection.suggested_connection is not None:
            connection = (
                f"{row.connection_rating_a:.0f} A"
                if row.connection_rating_a is not None
                else "Fixed"
            )
        schedule.append(
            {
                "Circuit": row.circuit_id,
                "Description": row.description,
                "Phase": row.assigned_phase + (" 🔒" if row.phase_locked and row.phase == "single" else ""),
                "Load": f"{row.load_value:g} kW",
                "Demand": f"{row.demand_factor:.2f}",
                "Ib": f"{row.design_current_a:.1f} A",
                "Breaker": f"{row.breaker_a:.0f} A" if row.breaker_a is not None else "—",
                "Cable": cable,
                "Connection": connection,
                "Scope": row.scope_status.replace("_", " "),
            }
        )
    st.dataframe(schedule, hide_index=True, use_container_width=True)

    blocking = tuple(
        circuit
        for circuit in result.circuits
        if circuit.verification.blocking_issues
    )
    if blocking:
        with st.expander("Needs verification"):
            for circuit in blocking:
                st.markdown(
                    f"**{circuit.request.circuit_id} · {circuit.request.description}**"
                )
                for issue in circuit.verification.blocking_issues:
                    st.write(f"• {issue.message}")

    with st.expander("Board planning assumptions"):
        st.write(f"• {incomer.basis}")
        st.write(
            "• Automatic phase allocation is a largest-first load-balancing heuristic; no acceptable phase-imbalance threshold is being asserted."
        )
        st.write(
            "• Board-level diversity, final incomer protection verification, board/busbar rating, ways, selectivity and fault-level checks are not implemented yet."
        )

st.caption(
    "Planning preview: circuit calculations come from the shared electrical engine. "
    "Board-level diversity and final protection verification are not yet implemented."
)
