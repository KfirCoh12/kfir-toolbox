"""Hierarchy-first board planning UI with a live single-line view."""
import streamlit as st
import streamlit.components.v1 as components

from src.board_graph import (
    add_radial_circuit,
    board_plan_request_from_graph,
    enrich_graph_with_plan,
    make_radial_board_graph,
)
from src.board_planner import calculate_board_plan
from src.single_line_svg import render_board_graph_svg

st.set_page_config(
    page_title="Board Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {max-width: 1500px; padding-top: 1.6rem; padding-bottom: 3rem;}
.hero {padding: 0.5rem 0 1rem 0;}
.hero h1 {margin:0; font-size:2.25rem; letter-spacing:-0.03em;}
.hero p {margin:.45rem 0 0 0; color:#94a3b8; font-size:1rem;}
.eyebrow {font-size:.74rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.35rem;}
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {border-radius:10px !important;}
[data-testid="stNumberInput"],
[data-testid="stSelectbox"],
[data-testid="stTextInput"] {max-width:280px;}
div.stButton > button {min-height:2.8rem; border-radius:12px; font-weight:700;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px; background:#111827; border-color:#263449;}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1rem 1.15rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #263449; border-radius:14px; padding:.9rem;}
.tree-note {color:#64748b; font-size:.82rem; margin-top:-.35rem;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="hero"><div class="eyebrow">Electrical engineering · Hierarchy preview</div><h1>⚡ Board Planner</h1><p>Build the electrical hierarchy on the left. The single-line diagram updates from the same model as you work.</p></div>""",
    unsafe_allow_html=True,
)


def default_circuits():
    return [
        {
            "uid": "seed-1",
            "circuit_id": "C-01",
            "description": "Lighting",
            "load_kw": 2.0,
            "phase": "single",
            "power_factor": 0.90,
            "demand_factor": 1.00,
            "material": "copper",
            "phase_preference": "Auto",
        },
        {
            "uid": "seed-2",
            "circuit_id": "C-02",
            "description": "Sockets",
            "load_kw": 3.0,
            "phase": "single",
            "power_factor": 0.90,
            "demand_factor": 0.80,
            "material": "copper",
            "phase_preference": "Auto",
        },
        {
            "uid": "seed-3",
            "circuit_id": "C-03",
            "description": "Three-phase load",
            "load_kw": 12.0,
            "phase": "three",
            "power_factor": 0.90,
            "demand_factor": 1.00,
            "material": "copper",
            "phase_preference": "Auto",
        },
    ]


if "tree_board_circuits" not in st.session_state:
    st.session_state["tree_board_circuits"] = default_circuits()
if "tree_uid_counter" not in st.session_state:
    st.session_state["tree_uid_counter"] = 100

circuits = st.session_state["tree_board_circuits"]
for index, circuit in enumerate(circuits):
    circuit.setdefault("uid", f"legacy-{index}")

header_left, header_right = st.columns([1, 1])
with header_left:
    board_id = st.text_input("Board ID", value="DB-01", key="tree_board_id")
with header_right:
    description = st.text_input(
        "Board description", value="Distribution board", key="tree_board_description"
    )

with st.expander("Board supply"):
    v1, v2, _ = st.columns([1, 1, 2])
    with v1:
        voltage_ll = st.number_input(
            "Line-line voltage (V)", min_value=1.0, value=400.0, step=5.0, key="tree_vll"
        )
    with v2:
        voltage_ln = st.number_input(
            "Line-neutral voltage (V)", min_value=1.0, value=230.0, step=5.0, key="tree_vln"
        )

left, right = st.columns([0.82, 1.18], gap="large")

with left:
    st.markdown("### Electrical hierarchy")
    st.markdown(
        '<div class="tree-note">Select a node to inspect or edit it. The schedule is now a generated view, not the design model.</div>',
        unsafe_allow_html=True,
    )

    add_col, delete_col = st.columns(2)
    with add_col:
        if st.button("＋ Add outgoing circuit", use_container_width=True):
            existing = {str(c["circuit_id"]).strip() for c in circuits}
            number = 1
            while f"C-{number:02d}" in existing:
                number += 1
            st.session_state["tree_uid_counter"] += 1
            uid = f"c{st.session_state['tree_uid_counter']}"
            circuits.append(
                {
                    "uid": uid,
                    "circuit_id": f"C-{number:02d}",
                    "description": "New load",
                    "load_kw": 1.0,
                    "phase": "single",
                    "power_factor": 0.90,
                    "demand_factor": 1.00,
                    "material": "copper",
                    "phase_preference": "Auto",
                }
            )
            st.session_state["tree_next_selected_node"] = f"circuit:{uid}:load"
            st.session_state.pop("tree_board_plan", None)
            st.rerun()

    node_ids = ["source", "incomer", "busbar"]
    labels = {
        "source": "⚡ Supply",
        "incomer": "   └─ Main incomer",
        "busbar": "       └─ Main busbar",
    }
    node_to_circuit_index = {}
    for index, circuit in enumerate(circuits):
        uid = circuit["uid"]
        cid = str(circuit["circuit_id"]).strip() or f"row-{index + 1}"
        device_token = f"circuit:{uid}:device"
        cable_token = f"circuit:{uid}:cable"
        load_token = f"circuit:{uid}:load"
        node_ids.extend([device_token, cable_token, load_token])
        branch = "├─" if index < len(circuits) - 1 else "└─"
        labels[device_token] = f"           {branch} {cid} · Protection"
        labels[cable_token] = "           │   └─ Cable"
        labels[load_token] = f"           │       └─ {circuit['description']}"
        for token in (device_token, cable_token, load_token):
            node_to_circuit_index[token] = index

    pending_selection = st.session_state.pop("tree_next_selected_node", None)
    if pending_selection is not None:
        st.session_state["tree_selected_node"] = pending_selection
    current_selected = st.session_state.get("tree_selected_node", "busbar")
    if current_selected not in node_ids:
        st.session_state["tree_selected_node"] = "busbar"

    selected_node = st.radio(
        "Electrical hierarchy",
        node_ids,
        format_func=lambda node_id: labels[node_id],
        label_visibility="collapsed",
        key="tree_selected_node",
    )

    selected_index = node_to_circuit_index.get(selected_node)
    with delete_col:
        delete_disabled = selected_index is None
        if st.button(
            "Delete selected circuit",
            disabled=delete_disabled,
            use_container_width=True,
        ):
            circuits.pop(selected_index)
            st.session_state["tree_next_selected_node"] = "busbar"
            st.session_state.pop("tree_board_plan", None)
            st.rerun()

    st.markdown("### Properties")
    if selected_node == "source":
        with st.container(border=True):
            st.markdown("**Incoming supply**")
            st.write(f"{voltage_ll:g} / {voltage_ln:g} V")
            st.caption("Supply/source details will expand later with upstream network and fault-level data.")
    elif selected_node == "incomer":
        with st.container(border=True):
            st.markdown("**Main incomer**")
            st.caption("The provisional rating appears after board calculation. Device family and protection verification are not implemented yet.")
    elif selected_node == "busbar":
        with st.container(border=True):
            st.markdown("**Main busbar**")
            st.caption("Outgoing branches are connected here. Busbar rating and board construction are not selected yet.")
    else:
        circuit = circuits[selected_index]
        uid = circuit["uid"]
        with st.container(border=True):
            id_col, phase_col = st.columns(2)
            with id_col:
                new_id = st.text_input(
                    "Circuit ID",
                    value=str(circuit["circuit_id"]),
                    key=f"tree_cid_{uid}",
                )
            with phase_col:
                phase_label = st.selectbox(
                    "Phase",
                    ["Single-phase", "Three-phase"],
                    index=0 if circuit["phase"] == "single" else 1,
                    key=f"tree_phase_{uid}",
                )
            new_phase = "single" if phase_label == "Single-phase" else "three"

            new_description = st.text_input(
                "Load / consumer",
                value=str(circuit["description"]),
                key=f"tree_desc_{uid}",
            )
            load_col, pf_col = st.columns(2)
            with load_col:
                new_load = st.number_input(
                    "Expected load (kW)",
                    min_value=0.1,
                    value=float(circuit["load_kw"]),
                    step=0.5,
                    key=f"tree_load_{uid}",
                    help="Input the expected load of the consumer.",
                )
            with pf_col:
                new_pf = st.number_input(
                    "Power factor",
                    min_value=0.01,
                    max_value=1.0,
                    value=float(circuit["power_factor"]),
                    step=0.01,
                    key=f"tree_pf_{uid}",
                )

            demand_col, material_col = st.columns(2)
            with demand_col:
                new_demand = st.number_input(
                    "Demand factor",
                    min_value=0.01,
                    max_value=1.0,
                    value=float(circuit["demand_factor"]),
                    step=0.05,
                    key=f"tree_demand_{uid}",
                )
            with material_col:
                material_label = st.selectbox(
                    "Conductor material",
                    ["Copper", "Aluminium"],
                    index=0 if circuit["material"] == "copper" else 1,
                    key=f"tree_material_{uid}",
                )
            new_material = "copper" if material_label == "Copper" else "aluminium"

            phase_preference = "Auto"
            if new_phase == "single":
                current_preference = circuit.get("phase_preference", "Auto")
                if current_preference not in ("Auto", "L1", "L2", "L3"):
                    current_preference = "Auto"
                phase_preference = st.selectbox(
                    "Phase assignment",
                    ["Auto", "L1", "L2", "L3"],
                    index=["Auto", "L1", "L2", "L3"].index(current_preference),
                    key=f"tree_lock_{uid}",
                    help="Leave Auto to let the planner balance this single-phase load.",
                )

        changed = (
            new_id.strip() != str(circuit["circuit_id"]).strip()
            or new_description != circuit["description"]
            or new_load != circuit["load_kw"]
            or new_phase != circuit["phase"]
            or new_pf != circuit["power_factor"]
            or new_demand != circuit["demand_factor"]
            or new_material != circuit["material"]
            or phase_preference != circuit.get("phase_preference", "Auto")
        )
        if changed:
            circuit.update(
                {
                    "circuit_id": new_id.strip(),
                    "description": new_description,
                    "load_kw": float(new_load),
                    "phase": new_phase,
                    "power_factor": float(new_pf),
                    "demand_factor": float(new_demand),
                    "material": new_material,
                    "phase_preference": phase_preference if new_phase == "single" else "Auto",
                }
            )
            st.session_state.pop("tree_board_plan", None)
            st.rerun()


def build_draft_graph():
    graph = make_radial_board_graph(
        board_id=board_id,
        description=description,
        line_to_line_voltage_v=float(voltage_ll),
        line_to_neutral_voltage_v=float(voltage_ln),
    )
    for circuit in circuits:
        graph = add_radial_circuit(
            graph,
            circuit_id=str(circuit["circuit_id"]),
            description=str(circuit["description"]),
            load_kw=float(circuit["load_kw"]),
            phase=circuit["phase"],
            power_factor=float(circuit["power_factor"]),
            demand_factor=float(circuit["demand_factor"]),
            material=circuit["material"],
            phase_preference=circuit.get("phase_preference", "Auto"),
        )
    return graph


def graph_signature():
    return (
        board_id.strip(),
        description.strip(),
        float(voltage_ll),
        float(voltage_ln),
        tuple(
            (
                str(c["circuit_id"]).strip(),
                str(c["description"]),
                float(c["load_kw"]),
                c["phase"],
                float(c["power_factor"]),
                float(c["demand_factor"]),
                c["material"],
                c.get("phase_preference", "Auto"),
            )
            for c in circuits
        ),
    )


try:
    draft_graph = build_draft_graph()
    graph_error = None
except (TypeError, ValueError) as exc:
    draft_graph = None
    graph_error = str(exc)

signature = graph_signature()
stored = st.session_state.get("tree_board_plan")
if stored and stored["signature"] != signature:
    st.session_state.pop("tree_board_plan", None)
    stored = None

with right:
    st.markdown("### Live single-line diagram")
    st.caption("The drawing follows the draft hierarchy immediately. Calculated values enrich it after planning.")

    if graph_error:
        st.error(graph_error)
    elif draft_graph is not None:
        display_graph = draft_graph
        if stored:
            display_graph = enrich_graph_with_plan(draft_graph, stored["result"])
        svg = render_board_graph_svg(display_graph)
        branch_count = len(circuits)
        height = max(500, min(900, 430 + branch_count * 18))
        components.html(svg, height=height, scrolling=True)

    calculate = st.button("Calculate board", type="primary", use_container_width=True)
    if calculate:
        try:
            if draft_graph is None:
                raise ValueError(graph_error or "Board hierarchy is not valid.")
            request = board_plan_request_from_graph(draft_graph)
            result = calculate_board_plan(request)
            st.session_state["tree_board_plan"] = {
                "signature": signature,
                "result": result,
            }
            st.rerun()
        except (TypeError, ValueError) as exc:
            st.session_state.pop("tree_board_plan", None)
            st.error(str(exc))

    if stored:
        result = stored["result"]
        if result.scope_status == "SUPPORTED_SCOPE":
            st.success("Calculated inside the currently supported circuit scope.")
        else:
            st.warning("Some circuit checks remain outside the supported scope; available values are shown without filling the gaps.")

        incomer = result.incomer_candidate
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(
            "Incomer",
            f"{incomer.breaker_rating_a:.0f} A" if incomer.breaker_rating_a is not None else "—",
        )
        m2.metric("L1", f"{result.phase_balance.l1_current_a:.1f} A")
        m3.metric("L2", f"{result.phase_balance.l2_current_a:.1f} A")
        m4.metric("L3", f"{result.phase_balance.l3_current_a:.1f} A")
        m5.metric("Spread", f"{result.phase_balance.spread_a:.1f} A")

        with st.expander("Generated circuit schedule"):
            schedule = []
            for row in result.schedule_rows:
                cable = "—"
                if row.cable_mm2 is not None:
                    cable = (
                        f"{row.cable_runs} × {row.cable_mm2:g} mm²"
                        if (row.cable_runs or 1) > 1
                        else f"{row.cable_mm2:g} mm²"
                    )
                schedule.append(
                    {
                        "Circuit": row.circuit_id,
                        "Load": row.description,
                        "Phase": row.assigned_phase,
                        "Ib": f"{row.design_current_a:.1f} A",
                        "Breaker": f"{row.breaker_a:.0f} A" if row.breaker_a is not None else "—",
                        "Cable": cable,
                        "Scope": row.scope_status.replace("_", " "),
                    }
                )
            st.dataframe(schedule, hide_index=True, use_container_width=True)

        blocking = tuple(c for c in result.circuits if c.verification.blocking_issues)
        if blocking:
            with st.expander("Needs verification"):
                for circuit_result in blocking:
                    st.markdown(
                        f"**{circuit_result.request.circuit_id} · {circuit_result.request.description}**"
                    )
                    for issue in circuit_result.verification.blocking_issues:
                        st.write(f"• {issue.message}")

        with st.expander("Board planning assumptions"):
            st.write(f"• {incomer.basis}")
            st.write("• Automatic phase allocation is a planning heuristic, not an imbalance-compliance check.")
            st.write("• Board-level diversity, final incomer protection verification, busbar rating, selectivity and fault-level checks are not implemented yet.")

st.caption(
    "Hierarchy preview: the electrical tree is the source model. The schedule and single-line diagram are generated views of that same structure."
)
