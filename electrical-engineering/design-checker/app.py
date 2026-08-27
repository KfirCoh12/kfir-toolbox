"""Two-mode Streamlit UI for Electrical Design Checker."""
import streamlit as st

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.circuit_selector import (
    CircuitSelectionInput,
    assess_installation_support,
    explain_circuit_selection,
    select_material_options,
)
from src.connection import connection_options_for_phase
from src.manufacturer_ampacity import get_nhxh_phase_conductor_mm2
from src.max_load import MaxLoadInput, calculate_max_load

st.set_page_config(
    page_title="Electrical Design Checker",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {max-width: 1220px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 0.8rem 0 1rem 0;}
.hero h1 {margin:0; font-size:2.35rem; letter-spacing:-0.03em;}
.hero p {margin:.55rem 0 0 0; color:#94a3b8; font-size:1rem;}
.eyebrow {font-size:.76rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.4rem;}
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {border-radius:10px !important;}
[data-testid="stNumberInput"],
[data-testid="stSelectbox"],
[data-testid="stTextInput"] {max-width:260px;}
div.stButton > button {min-height:3rem; border-radius:12px; font-weight:700;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px; background:#111827; border-color:#263449;}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1.15rem 1.25rem;}
[data-testid="stRadio"] {margin-bottom:.7rem;}
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
    """<div class="hero"><div class="eyebrow">Electrical engineering · V0.10</div><h1>⚡ Electrical Design Checker</h1><p>Size a new supply or find the usable capacity of electrical equipment you already have.</p></div>""",
    unsafe_allow_html=True,
)

mode = st.radio(
    "What do you want to do?",
    ["Design a supply", "Existing supply capacity"],
    horizontal=True,
    label_visibility="collapsed",
)


def generic_route(material, size, ambient, grouped, arrangement):
    cable = CableAmpacityInput(
        material=material,
        cross_section_mm2=float(size),
        insulation="xlpe_epr",
        loaded_conductors=3,
        installation_method="E",
        environment="air",
        ambient_temperature_c=float(ambient),
        grouped_circuits=int(grouped),
        grouping_arrangement=arrangement,
        parallel_runs=1,
        equal_current_sharing_confirmed=None,
        thdi_percent=0.0,
        neutral_loaded=False,
    )
    return cable, RoutedAmpacityInput(source_kind="iec_generic", generic=cable)


def source_inputs(prefix=""):
    source = st.selectbox(
        "Cable source",
        ["Generic XLPE/EPR · IEC", "NHXH FE180/E90 · Manufacturer"],
        key=f"{prefix}source",
        help="Choose the data source that matches the existing cable.",
    )
    if source.startswith("Generic"):
        material = st.selectbox(
            "Conductor material", ["copper", "aluminium"], key=f"{prefix}mat"
        )
        sizes = [10, 25, 95, 120, 185, 240]
        size = st.selectbox("Phase conductor (mm²)", sizes, key=f"{prefix}size")
        ambient = 30
        grouped = 1
        arrangement = None
        with st.expander("Advanced cable conditions"):
            ambient = st.selectbox(
                "Ambient air temperature (°C)",
                [20, 25, 30, 35, 40, 45, 50],
                index=2,
                key=f"{prefix}amb",
            )
            grouped = st.number_input(
                "Grouped circuits / cables",
                min_value=1,
                value=1,
                step=1,
                key=f"{prefix}grp",
                help="Total loaded circuits or cables installed together.",
            )
            if grouped > 1:
                arrangement = st.selectbox(
                    "Grouping arrangement",
                    [
                        "bunched",
                        "perforated_tray_single_layer",
                        "ladder_single_layer",
                    ],
                    key=f"{prefix}arr",
                    help="Physical arrangement used for the grouping correction.",
                )
        cable, route = generic_route(material, size, ambient, grouped, arrangement)
        return source, material, float(size), route, cable

    st.caption("NHXH FE180/E90 · copper · air · 30 °C")
    construction = st.selectbox(
        "Cable construction",
        ["5x10", "5x25", "3x95+50", "3x120+70"],
        key=f"{prefix}const",
    )
    size = get_nhxh_phase_conductor_mm2(construction)
    route = RoutedAmpacityInput(
        source_kind="manufacturer_nhxh_fe180_e90",
        construction=construction,
        ambient_temperature_c=30.0,
        grouped_circuits=1,
        parallel_runs=1,
    )
    return source, "copper", float(size), route, None


if mode == "Design a supply":
    st.subheader("Design a supply")

    with st.container(border=True):
        st.caption("LOAD → CURRENT → PROTECTION → CABLE")

        st.markdown("#### Load")
        load_col, demand_col, _ = st.columns([1, 1, 2])
        with load_col:
            load_kw = st.number_input(
                "Consumer load (kW)",
                min_value=0.1,
                value=30.0,
                step=1.0,
                help="Input the expected load of the consumer.",
            )
        with demand_col:
            demand = st.number_input(
                "Demand factor",
                min_value=0.01,
                max_value=1.0,
                value=0.80,
                step=0.05,
                help="Fraction of the connected load expected to operate at the same time.",
            )

        phase_col, voltage_col, pf_col, _ = st.columns([1, 1, 1, 1])
        with phase_col:
            phase_label = st.selectbox(
                "Phase", ["Three-phase", "Single-phase"], key="design_phase"
            )
        phase = "three" if phase_label == "Three-phase" else "single"
        with voltage_col:
            voltage = st.number_input(
                "System voltage (V)",
                min_value=1.0,
                value=400.0 if phase == "three" else 230.0,
                step=10.0,
                key="design_voltage",
            )
        with pf_col:
            pf = st.number_input(
                "Power factor",
                min_value=0.01,
                max_value=1.0,
                value=0.90,
                step=0.01,
                help="Expected operating power factor of the load.",
            )

        if phase == "single":
            st.caption(
                "Single-phase mode can calculate Ib, a conventional breaker candidate and a "
                "connection rating. Automatic cable sizing remains NOT VERIFIED because the "
                "current ampacity dataset covers three loaded conductors only."
            )

        st.markdown("#### Installation")
        ambient = 30
        grouped = 1
        arrangement = None
        parallel_runs = 1
        equal_current_sharing = None

        with st.expander("Advanced installation conditions"):
            st.caption("Automatic sizing dataset: Method E · air · 30 °C.")
            if phase == "three":
                parallel_runs = st.number_input(
                    "Parallel cable runs per phase",
                    min_value=1,
                    value=1,
                    step=1,
                    key="design_parallel_runs",
                    help="Number of identical cables connected in parallel per phase.",
                )
                if parallel_runs > 1:
                    equal_current_sharing = st.checkbox(
                        "I confirm the parallel runs are arranged for acceptable current sharing",
                        value=False,
                        key="design_equal_share",
                    )
                    st.caption(
                        "Grouping must include every parallel run before aggregate ampacity is used."
                    )

            grouped = st.number_input(
                "Number of grouped circuits / cables",
                min_value=1,
                value=max(1, int(parallel_runs)),
                step=1,
                key="design_grouped",
                help="Total loaded circuits or cables installed together.",
            )
            if grouped > 1:
                arrangement = st.selectbox(
                    "Grouping arrangement",
                    [
                        "bunched",
                        "perforated_tray_single_layer",
                        "ladder_single_layer",
                    ],
                    format_func=lambda x: {
                        "bunched": "Bunched together",
                        "perforated_tray_single_layer": "Single layer on perforated tray",
                        "ladder_single_layer": "Single layer on ladder",
                    }[x],
                    help="Physical arrangement used for the grouping correction.",
                )

        support_inputs = dict(
            load_type="kw",
            load_value=load_kw,
            voltage_v=voltage,
            phase=phase,
            power_factor=pf,
            demand_factor=demand,
            ambient_temperature_c=ambient,
            grouped_circuits=grouped,
            grouping_arrangement=arrangement,
            parallel_runs=int(parallel_runs),
            equal_current_sharing_confirmed=equal_current_sharing,
        )
        copper_support = assess_installation_support(
            CircuitSelectionInput(material="copper", **support_inputs)
        )
        aluminium_support = assess_installation_support(
            CircuitSelectionInput(material="aluminium", **support_inputs)
        )
        installation_supported = (
            copper_support.status == "SUPPORTED"
            and aluminium_support.status == "SUPPORTED"
        )

        if not installation_supported:
            st.warning("Cable auto-sizing: NOT VERIFIED for the current installation conditions.")
            with st.expander("Why cable sizing is not verified"):
                for material_label, support in (
                    ("Copper", copper_support),
                    ("Aluminium", aluminium_support),
                ):
                    st.markdown(f"**{material_label}: {support.status}**")
                    for reason in support.missing_or_unsupported:
                        st.write("•", reason)

        st.markdown("#### Voltage drop")
        check_vd = st.checkbox(
            "Check voltage drop",
            value=False,
            help="Optional. Enable this if cable length should be included in the sizing check.",
        )
        length = None
        vd_limit = 5.0
        vd_source = "Project criterion"
        annex = True

        if check_vd:
            length_col, _ = st.columns([1, 3])
            with length_col:
                length = st.number_input(
                    "Cable length (m)", min_value=0.1, value=50.0, step=5.0
                )
            with st.expander("Advanced voltage-drop settings"):
                vd_limit = st.number_input(
                    "Maximum permitted drop (%)",
                    min_value=0.1,
                    value=5.0,
                    step=0.5,
                    help="Maximum voltage drop allowed by the project criterion.",
                )
                vd_source = st.text_input("Limit source", value="Project criterion")
                annex = st.checkbox(
                    "Use IEC Annex G fallback impedance assumptions", value=True
                )

    design_signature = (
        float(load_kw),
        float(demand),
        phase,
        float(voltage),
        float(pf),
        int(grouped),
        arrangement,
        int(parallel_runs),
        equal_current_sharing,
        bool(check_vd),
        float(length) if length is not None else None,
        float(vd_limit) if check_vd else None,
        vd_source.strip() if check_vd else None,
        bool(annex) if check_vd else False,
    )

    calculate_design = st.button("Suggest supply", type="primary", use_container_width=True)

    if calculate_design:
        try:
            options = select_material_options(
                CircuitSelectionInput(
                    load_type="kw",
                    load_value=load_kw,
                    voltage_v=voltage,
                    phase=phase,
                    power_factor=pf,
                    demand_factor=demand,
                    ambient_temperature_c=ambient,
                    grouped_circuits=grouped,
                    grouping_arrangement=arrangement,
                    parallel_runs=int(parallel_runs),
                    equal_current_sharing_confirmed=equal_current_sharing,
                    length_m=length if check_vd else None,
                    permitted_voltage_drop_percent=vd_limit if check_vd else None,
                    voltage_drop_limit_source=(vd_source.strip() or None) if check_vd else None,
                    allow_annex_g_defaults=annex if check_vd else False,
                )
            )
            st.session_state["design_result"] = {
                "signature": design_signature,
                "options": options,
            }
        except ValueError as exc:
            st.session_state.pop("design_result", None)
            st.error(str(exc))

    stored_design_result = st.session_state.get("design_result")
    if stored_design_result and stored_design_result["signature"] != design_signature:
        st.session_state.pop("design_result", None)
        stored_design_result = None

    if stored_design_result:
        options = stored_design_result["options"]
        r = options.copper
        r_al = options.aluminium

        if r.status == "SUGGESTION":
            st.success("A provisional sizing suggestion was found from the currently supported data.")
        elif r.status == "NO SUPPORTED SOLUTION":
            st.error("No solution was found inside the current supported dataset.")
        else:
            st.warning(
                "A complete automatic suggestion is not verified for these inputs. "
                "Verified numerical parts are shown; unsupported parts remain blank."
            )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Design current · Ib", f"{r.current.design_current_a:.1f} A")
        c2.metric(
            "Suggested breaker",
            f"{r.suggested_breaker_a:.0f} A" if r.suggested_breaker_a else "—",
        )
        copper_label = (
            f"{r.suggested_parallel_runs} × {r.suggested_cable_mm2:g} mm²"
            if r.suggested_cable_mm2 and (r.suggested_parallel_runs or 1) > 1
            else f"{r.suggested_cable_mm2:g} mm²"
            if r.suggested_cable_mm2
            else "—"
        )
        c3.metric("Copper cable", copper_label)
        aluminium_label = (
            f"{r_al.suggested_parallel_runs} × {r_al.suggested_cable_mm2:g} mm²"
            if r_al.suggested_cable_mm2 and (r_al.suggested_parallel_runs or 1) > 1
            else f"{r_al.suggested_cable_mm2:g} mm²"
            if r_al.suggested_cable_mm2
            else "—"
        )
        c4.metric("Aluminium cable", aluminium_label)
        c5.metric(
            "Connection",
            f"{r.suggested_connection.rating_a:.0f} A"
            if r.suggested_connection and r.suggested_connection.rating_a
            else "Fixed",
        )

        explanation = explain_circuit_selection(r)
        with st.expander("Why this suggestion?"):
            st.write(f"**{explanation.summary}**")
            st.write("**Breaker:**", explanation.breaker_reason)
            st.write("**Copper cable:**", explanation.cable_reason)
            st.write("**Connection:**", explanation.connection_reason)
            if explanation.voltage_drop_reason:
                st.write("**Voltage drop:**", explanation.voltage_drop_reason)
            if explanation.why_not_smaller:
                st.markdown("**Why not a smaller copper cable?**")
                for reason in explanation.why_not_smaller:
                    st.write("•", reason)
            if r.suggested_cable_mm2 and r_al.suggested_cable_mm2:
                st.markdown("**Cable comparison**")
                left, right = st.columns(2)
                with left:
                    st.write(
                        f"**Copper {copper_label}** · aggregate Iz {r.cable_iz_a:.1f} A"
                        + (
                            f" · voltage drop {r.voltage_drop.voltage_drop_percent:.2f}%"
                            if r.voltage_drop
                            else ""
                        )
                    )
                with right:
                    st.write(
                        f"**Aluminium {aluminium_label}** · aggregate Iz {r_al.cable_iz_a:.1f} A"
                        + (
                            f" · voltage drop {r_al.voltage_drop.voltage_drop_percent:.2f}%"
                            if r_al.voltage_drop
                            else ""
                        )
                    )

        if r.limitations:
            with st.expander("Important limitations"):
                for x in r.limitations:
                    st.write("•", x)

else:
    st.subheader("Existing supply capacity")

    with st.container(border=True):
        st.caption("KNOWN COMPONENT(S) → LOWEST CURRENT LIMIT → MAXIMUM kW")
        st.markdown("#### What do you already have?")

        known_breaker_col, known_cable_col, known_connection_col = st.columns(3)
        with known_breaker_col:
            use_breaker = st.checkbox(
                "Breaker",
                value=True,
                key="cap_have_breaker",
                help="Use this if the protective device rating is known.",
            )
        with known_cable_col:
            use_cable = st.checkbox(
                "Cable",
                value=False,
                key="cap_have_cable",
                help="Use this if the existing cable construction is known.",
            )
        with known_connection_col:
            use_connection = st.checkbox(
                "Outlet / connection",
                value=False,
                key="cap_have_conn",
                help="Use this if the outlet or connection rating is known.",
            )

        breaker = None
        if use_breaker:
            breaker_col, _ = st.columns([1, 3])
            with breaker_col:
                breaker = st.number_input(
                    "Breaker rating In (A)",
                    min_value=1.0,
                    value=63.0,
                    step=1.0,
                    key="cap_breaker",
                    help="Rated current printed on the breaker or protective device.",
                )

        material = "copper"
        size = None
        route = None
        source = None
        if use_cable:
            st.markdown("##### Existing cable")
            source, material, size, route, _ = source_inputs("cap_")

        st.markdown("#### Electrical system")
        phase_col, voltage_col, pf_col, _ = st.columns([1, 1, 1, 1])
        with phase_col:
            phase_label = st.selectbox(
                "Phase", ["Three-phase", "Single-phase"], key="cap_phase"
            )
        phase = "three" if phase_label == "Three-phase" else "single"
        with voltage_col:
            voltage = st.number_input(
                "System voltage (V)",
                min_value=1.0,
                value=400.0 if phase == "three" else 230.0,
                step=10.0,
                key="cap_v",
            )
        with pf_col:
            pf = st.number_input(
                "Power factor",
                min_value=0.01,
                max_value=1.0,
                value=0.90,
                step=0.01,
                key="cap_pf",
                help="Expected operating power factor of the load.",
            )

        connection_option_id = None
        selected_label = None
        if use_connection:
            options = connection_options_for_phase(phase, include_fixed=False)
            option_labels = {x.label: x.id for x in options}
            connection_col, _ = st.columns([1, 3])
            with connection_col:
                selected_label = st.selectbox(
                    "Outlet / connection",
                    list(option_labels.keys()),
                    key="cap_conn",
                    help="Select the known outlet or connection rating.",
                )
            connection_option_id = option_labels[selected_label]

        use_vd = False
        length = None
        vd_limit = 5.0
        vd_source = "Project criterion"
        annex = True
        if use_cable:
            st.markdown("#### Voltage drop")
            use_vd = st.checkbox(
                "Use cable length to limit capacity",
                value=False,
                key="cap_use_vd",
                help="Optional. Enable this when voltage drop should also set the capacity ceiling.",
            )
            if use_vd:
                length_col, _ = st.columns([1, 3])
                with length_col:
                    length = st.number_input(
                        "Cable length (m)",
                        min_value=0.1,
                        value=50.0,
                        step=5.0,
                        key="cap_len",
                    )
                with st.expander("Advanced voltage-drop settings"):
                    vd_limit = st.number_input(
                        "Maximum permitted drop (%)",
                        min_value=0.1,
                        value=5.0,
                        step=0.5,
                        key="cap_vdl",
                        help="Maximum voltage drop allowed by the project criterion.",
                    )
                    vd_source = st.text_input(
                        "Limit source", value="Project criterion", key="cap_vds"
                    )
                    annex = st.checkbox(
                        "Use IEC Annex G fallback impedance assumptions",
                        value=True,
                        key="cap_annex",
                    )

    capacity_signature = (
        bool(use_breaker),
        float(breaker) if breaker is not None else None,
        bool(use_cable),
        source,
        material if use_cable else None,
        float(size) if size is not None else None,
        repr(route) if route is not None else None,
        bool(use_connection),
        connection_option_id,
        phase,
        float(voltage),
        float(pf),
        bool(use_vd),
        float(length) if length is not None else None,
        float(vd_limit) if use_vd else None,
        vd_source.strip() if use_vd else None,
        bool(annex) if use_vd else False,
    )

    calculate_capacity = st.button(
        "Calculate existing capacity", type="primary", use_container_width=True
    )

    if calculate_capacity:
        if not (use_breaker or use_cable or use_connection):
            st.session_state.pop("capacity_result", None)
            st.error("Select at least one known component: breaker, cable, or outlet / connection.")
        else:
            try:
                result = calculate_max_load(
                    MaxLoadInput(
                        voltage_v=voltage,
                        phase=phase,
                        power_factor=pf,
                        breaker_in_a=breaker if use_breaker else None,
                        connection_option_id=connection_option_id if use_connection else None,
                        ampacity_route=route if use_cable else None,
                        length_m=length if use_vd else None,
                        voltage_drop_cross_section_mm2=size if use_vd and use_cable else None,
                        voltage_drop_material=material if use_vd and use_cable else None,
                        permitted_voltage_drop_percent=vd_limit if use_vd else None,
                        voltage_drop_limit_source=(vd_source.strip() or None) if use_vd else None,
                        allow_annex_g_defaults=annex if use_vd else False,
                    )
                )
                st.session_state["capacity_result"] = {
                    "signature": capacity_signature,
                    "result": result,
                }
            except ValueError as exc:
                st.session_state.pop("capacity_result", None)
                st.error(str(exc))

    stored_capacity_result = st.session_state.get("capacity_result")
    if stored_capacity_result and stored_capacity_result["signature"] != capacity_signature:
        st.session_state.pop("capacity_result", None)
        stored_capacity_result = None

    if stored_capacity_result:
        r = stored_capacity_result["result"]

        if r.status == "RESULT":
            if r.coverage_status == "FULL CORE COVERAGE":
                st.success(f"Capacity ceiling found. Limiting factor: {r.limiting_constraint}.")
            else:
                st.warning(
                    f"Provisional capacity ceiling found. Limiting factor: {r.limiting_constraint}."
                )
        else:
            st.warning("A capacity ceiling could not be verified from the supplied information.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Maximum current", f"{r.max_current_a:.1f} A" if r.max_current_a else "—")
        c2.metric("Maximum active load", f"{r.max_kw:.1f} kW" if r.max_kw else "—")
        c3.metric("Maximum apparent load", f"{r.max_kva:.1f} kVA" if r.max_kva else "—")

        if r.missing_core_checks:
            with st.expander("Still needs verification"):
                for x in r.missing_core_checks:
                    st.write("•", x)

        if r.constraints:
            with st.expander("What sets the ceiling?"):
                for x in sorted(r.constraints, key=lambda z: z.current_a):
                    label = "← LIMITING" if x.name == r.limiting_constraint else ""
                    st.write(f"**{x.name}: {x.current_a:.1f} A** {label} — {x.detail}")

        if r.limitations:
            with st.expander("Verification notes"):
                for x in r.limitations:
                    st.write("•", x)

        with st.expander("Calculation trace"):
            for x in r.trace:
                st.code(x)

st.caption(
    "V0.10 focuses on two practical questions: what supply should this load use, "
    "and what can the electrical equipment I already have support?"
)
