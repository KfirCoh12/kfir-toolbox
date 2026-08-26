"""Three-mode Streamlit UI for Electrical Design Checker V0.4."""
import streamlit as st

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.circuit_selector import CircuitSelectionInput, select_circuit, select_material_options
from src.connection import connection_options_for_phase
from src.manufacturer_ampacity import get_nhxh_phase_conductor_mm2
from src.max_load import MaxLoadInput, calculate_max_load

st.set_page_config(page_title="Electrical Design Checker", page_icon="â¡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container {max-width: 1220px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 0.8rem 0 1rem 0;}
.hero h1 {margin:0; font-size:2.35rem; letter-spacing:-0.03em;}
.hero p {margin:.55rem 0 0 0; opacity:.72; font-size:1rem;}
.eyebrow {font-size:.76rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; opacity:.55; margin-bottom:.4rem;}
[data-testid="stSidebar"] > div:first-child {padding-top:1.2rem;}
[data-testid="stSidebar"] h2 {margin-top:1.15rem; font-size:1.05rem;}
[data-baseweb="select"] > div, [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {border-radius:10px !important;}
div.stButton > button {min-height:3rem; border-radius:12px; font-weight:700;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px;}
.result-card {border:1px solid rgba(128,128,128,.22); border-radius:14px; padding:1rem 1.05rem; min-height:112px;}
.result-label {opacity:.68; font-size:.84rem; margin-bottom:.35rem;}
.result-value {font-size:2rem; font-weight:650; letter-spacing:-.025em; line-height:1.08;}
.result-note {margin-top:.45rem; opacity:.68; font-size:.83rem;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1.15rem 1.25rem;}
[data-testid="stRadio"] {margin-bottom:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><div class="eyebrow">Electrical engineering Â· V0.7</div><h1>â¡ Electrical Design Checker</h1><p>Size a new supply or find the usable capacity of an existing circuit.</p></div>""", unsafe_allow_html=True)

mode = st.radio(
    "What do you want to do?",
    ["Design a supply", "Existing supply capacity"],
    horizontal=True,
    label_visibility="collapsed",
)


def generic_route(material, size, ambient, grouped, arrangement):
    cable = CableAmpacityInput(
        material=material, cross_section_mm2=float(size), insulation="xlpe_epr",
        loaded_conductors=3, installation_method="E", environment="air",
        ambient_temperature_c=float(ambient), grouped_circuits=int(grouped),
        grouping_arrangement=arrangement, parallel_runs=1,
        equal_current_sharing_confirmed=None, thdi_percent=0.0, neutral_loaded=False,
    )
    return cable, RoutedAmpacityInput(source_kind="iec_generic", generic=cable)


def source_inputs(prefix=""):
    source = st.selectbox("Cable source", ["Generic XLPE/EPR Â· IEC", "NHXH FE180/E90 Â· Manufacturer"], key=f"{prefix}source")
    if source.startswith("Generic"):
        material = st.selectbox("Conductor material", ["copper", "aluminium"], key=f"{prefix}mat")
        sizes = [10, 25, 95, 120, 185, 240]
        size = st.selectbox("Phase conductor (mmÂ²)", sizes, key=f"{prefix}size")
        ambient = 30
        grouped = 1
        arrangement = None
        with st.expander("Advanced cable conditions"):
            ambient = st.selectbox("Ambient air temperature (Â°C)", [20,25,30,35,40,45,50], index=2, key=f"{prefix}amb")
            grouped = st.number_input("Grouped circuits / cables", min_value=1, value=1, step=1, key=f"{prefix}grp")
            if grouped > 1:
                arrangement = st.selectbox("Grouping arrangement", ["bunched", "perforated_tray_single_layer", "ladder_single_layer"], key=f"{prefix}arr")
        cable, route = generic_route(material,size,ambient,grouped,arrangement)
        return source, material, float(size), route, cable
    st.caption("Supported V0 manufacturer condition: copper NHXH FE180/E90, in air, 30 Â°C. Unsupported corrections remain unverified.")
    construction = st.selectbox("Cable construction", ["5x10", "5x25", "3x95+50", "3x120+70"], key=f"{prefix}const")
    size = get_nhxh_phase_conductor_mm2(construction)
    route = RoutedAmpacityInput(source_kind="manufacturer_nhxh_fe180_e90", construction=construction, ambient_temperature_c=30.0, grouped_circuits=1, parallel_runs=1)
    return source, "copper", float(size), route, None


if mode == "Design a supply":
    st.subheader("Design a supply")
    st.info("Enter the consumer kW and any other parameters you know. The tool calculates the expected design current and suggests a breaker, supported cable options, and connection rating. You do not need to choose a cable first.")
    with st.container(border=True):
        st.markdown("### Input workspace")
        st.caption("LOAD â CURRENT â PROTECTION â CABLE")
        st.header("Load")
        load_kw = st.number_input("Consumer load (kW)", min_value=0.1, value=30.0, step=1.0)
        demand = st.number_input("Usage / demand factor", min_value=0.01, max_value=1.0, value=0.80, step=0.05)
        voltage = st.number_input("System voltage (V)", min_value=1.0, value=400.0, step=10.0)
        pf = st.number_input("Power factor", min_value=0.01, max_value=1.0, value=0.90, step=0.01)
        st.header("Installation")
        st.caption("Cable material is compared automatically â no cable selection is required here.")
        ambient = 30
        grouped = 1
        arrangement = None
        with st.expander("Advanced cable conditions"):
            st.caption("Current automatic sizing uses the verified Method E (in-air) cable dataset at its 30 °C reference condition. Only change conditions that materially affect cable capacity.")
            grouped = st.number_input("Number of grouped circuits / cables", min_value=1, value=1, step=1)
            if grouped > 1:
                arrangement = st.selectbox("How are they grouped?", ["bunched", "perforated_tray_single_layer", "ladder_single_layer"], format_func=lambda x: {"bunched":"Bunched together", "perforated_tray_single_layer":"Single layer on perforated tray", "ladder_single_layer":"Single layer on ladder"}[x])
        st.header("Voltage drop")
        check_vd = st.checkbox("Include cable length", value=True)
        length = st.number_input("Cable length (m)", min_value=0.1, value=50.0, step=5.0, disabled=not check_vd)
        vd_limit = 5.0
        vd_source = "Project criterion"
        annex = True
        with st.expander("Advanced voltage-drop settings"):
            vd_limit = st.number_input("Maximum permitted drop (%)", min_value=0.1, value=5.0, step=0.5, disabled=not check_vd)
            vd_source = st.text_input("Limit source", value="Project criterion", disabled=not check_vd)
            annex = st.checkbox("Use IEC Annex G fallback impedance assumptions", value=True, disabled=not check_vd)
    if st.button("Suggest supply", type="primary", use_container_width=True):
        try:
            options = select_material_options(CircuitSelectionInput(load_type="kw",load_value=load_kw,voltage_v=voltage,phase="three",power_factor=pf,demand_factor=demand,ambient_temperature_c=ambient,grouped_circuits=grouped,grouping_arrangement=arrangement,length_m=length if check_vd else None,permitted_voltage_drop_percent=vd_limit if check_vd else None,voltage_drop_limit_source=(vd_source.strip() or None) if check_vd else None,allow_annex_g_defaults=annex if check_vd else False))
            r = options.copper
            r_al = options.aluminium
        except ValueError as exc:
            st.error(str(exc)); st.stop()
        if r.status == "SUGGESTION": st.success("A supported numerical supply suggestion was found.")
        elif r.status == "NO SUPPORTED SOLUTION": st.error("No solution was found inside the current supported dataset.")
        else: st.warning("A complete automatic suggestion is not verified for these inputs.")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Design current Â· Ib", f"{r.current.design_current_a:.1f} A")
        c2.metric("Suggested breaker", f"{r.suggested_breaker_a:.0f} A" if r.suggested_breaker_a else "â")
        c3.metric("Copper cable", f"{r.suggested_cable_mm2:g} mmÂ²" if r.suggested_cable_mm2 else "â")
        c4.metric("Aluminium cable", f"{r_al.suggested_cable_mm2:g} mmÂ²" if r_al.suggested_cable_mm2 else "â")
        c5.metric("Connection", f"{r.suggested_connection.rating_a:.0f} A" if r.suggested_connection and r.suggested_connection.rating_a else "Fixed")
        if r.suggested_cable_mm2 and r_al.suggested_cable_mm2:
            st.markdown("**Cable comparison**")
            left,right=st.columns(2)
            with left:
                st.write(f"**Copper {r.suggested_cable_mm2:g} mmÂ²** Â· Iz {r.cable_iz_a:.1f} A" + (f" Â· voltage drop {r.voltage_drop.voltage_drop_percent:.2f}%" if r.voltage_drop else ""))
            with right:
                st.write(f"**Aluminium {r_al.suggested_cable_mm2:g} mmÂ²** Â· Iz {r_al.cable_iz_a:.1f} A" + (f" Â· voltage drop {r_al.voltage_drop.voltage_drop_percent:.2f}%" if r_al.voltage_drop else ""))
            if r.suggested_cable_mm2 == r_al.suggested_cable_mm2:
                st.caption("The same nominal size can be valid for both materials when both independently satisfy breaker capacity and voltage-drop checks; their Iz and voltage-drop values can still differ.")
        if r.suggested_connection:
            st.info(f"Suggested connection rating: **{r.suggested_connection.label}**. This is used only as a current-limit recommendation.")
        if r.voltage_drop: st.info(f"Voltage drop: {r.voltage_drop.voltage_drop_percent:.2f}% Â· {r.voltage_drop.comparison}")
        if r.limitations:
            st.subheader("Important limitations")
            for x in r.limitations: st.warning(x)
        with st.expander("Why this suggestion?"):
            for x in r.trace: st.write("â¢",x)
            if r.rejected_candidates:
                st.markdown("**Copper smaller/rejected candidates**")
                for x in r.rejected_candidates: st.write("â¢",x)
            if r_al.rejected_candidates:
                st.markdown("**Aluminium smaller/rejected candidates**")
                for x in r_al.rejected_candidates: st.write("â¢",x)
    else:
        st.info("Start with the consumer kW. Add demand factor, voltage, power factor and cable length if known, then press **Suggest supply** â the tool will calculate current and cable options for you.")

else:
    st.subheader("Existing supply capacity")
    st.info("Enter what already exists — primarily the breaker and cable. The tool will calculate the maximum current and kW this setup can support, and show which part of the circuit is the limiting factor. You do not need to guess a load first.")
    with st.container(border=True):
        st.markdown("### Existing circuit")
        st.caption("BREAKER + CABLE → LIMITING CURRENT → MAXIMUM kW")

        left, right = st.columns(2)
        with left:
            st.markdown("#### 1. Breaker")
            breaker = st.number_input("Existing breaker rating In (A)", min_value=1.0, value=63.0, step=1.0, key="cap_breaker")
        with right:
            st.markdown("#### 2. Cable")
            _, material, size, route, _ = source_inputs("cap_")

        st.markdown("#### 3. Supply basics")
        c1, c2, c3 = st.columns(3)
        with c1:
            phase_label = st.selectbox("Phase", ["Three-phase", "Single-phase"], key="cap_phase")
            phase = "three" if phase_label == "Three-phase" else "single"
        with c2:
            voltage = st.number_input("System voltage (V)", min_value=1.0, value=400.0, step=10.0, key="cap_v")
        with c3:
            pf = st.number_input("Power factor", min_value=0.01, max_value=1.0, value=0.90, step=0.01, key="cap_pf")

        st.markdown("#### Optional limits")
        use_connection = st.checkbox("Include outlet / connection rating", value=False, key="cap_use_conn")
        connection_option_id = None
        connection = None
        if use_connection:
            options = connection_options_for_phase(phase, include_fixed=True)
            option_labels = {x.label: x.id for x in options}
            selected_label = st.selectbox("Outlet / connection", list(option_labels.keys()), key="cap_conn")
            connection_option_id = option_labels[selected_label]

        use_vd = st.checkbox("Include cable length / voltage drop as a limit", value=False, key="cap_use_vd")
        length = st.number_input("Cable length (m)", min_value=0.1, value=50.0, step=5.0, disabled=not use_vd, key="cap_len")
        vd_limit = 5.0
        vd_source = "Project criterion"
        annex = True
        with st.expander("Advanced voltage-drop settings"):
            vd_limit = st.number_input("Maximum permitted drop (%)", min_value=0.1, value=5.0, step=0.5, disabled=not use_vd, key="cap_vdl")
            vd_source = st.text_input("Limit source", value="Project criterion", disabled=not use_vd, key="cap_vds")
            annex = st.checkbox("Use IEC Annex G fallback impedance assumptions", value=True, disabled=not use_vd, key="cap_annex")

    if st.button("Calculate existing capacity", type="primary", use_container_width=True):
        try:
            r = calculate_max_load(MaxLoadInput(
                voltage_v=voltage,
                phase=phase,
                power_factor=pf,
                breaker_in_a=breaker,
                connection_option_id=connection_option_id if use_connection else None,
                ampacity_route=route,
                length_m=length if use_vd else None,
                voltage_drop_cross_section_mm2=size if use_vd else None,
                voltage_drop_material=material if use_vd else None,
                permitted_voltage_drop_percent=vd_limit if use_vd else None,
                voltage_drop_limit_source=(vd_source.strip() or None) if use_vd else None,
                allow_annex_g_defaults=annex if use_vd else False,
            ))
        except ValueError as exc:
            st.error(str(exc)); st.stop()

        if r.status == "RESULT":
            st.success(f"Usable ceiling found. Limiting factor: {r.limiting_constraint}.")
        else:
            st.warning("A maximum load could not be verified from the supported information supplied.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Maximum current", f"{r.max_current_a:.1f} A" if r.max_current_a else "—")
        c2.metric("Maximum active load", f"{r.max_kw:.1f} kW" if r.max_kw else "—")
        c3.metric("Maximum apparent load", f"{r.max_kva:.1f} kVA" if r.max_kva else "—")

        if r.constraints:
            st.subheader("What sets the ceiling?")
            for x in sorted(r.constraints, key=lambda z: z.current_a):
                label = "← LIMITING" if x.name == r.limiting_constraint else ""
                st.write(f"**{x.name}: {x.current_a:.1f} A** {label} — {x.detail}")

        if r.limitations:
            with st.expander("Verification notes"):
                for x in r.limitations: st.write("•", x)
        with st.expander("Calculation trace"):
            for x in r.trace: st.code(x)
    else:
        st.info("Start with the breaker and cable that are already installed. The result is a capacity ceiling — no trial load is required.")

st.caption("V0.8 focuses on two practical questions: what supply should this load use, and how much can this existing supply support?")
