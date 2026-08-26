"""Three-mode Streamlit UI for Electrical Design Checker V0.4."""
import streamlit as st

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.circuit_selector import CircuitSelectionInput, select_circuit
from src.connection import connection_options_for_phase
from src.feeder import FeederInput, check_feeder
from src.manufacturer_ampacity import get_nhxh_phase_conductor_mm2
from src.max_load import MaxLoadInput, calculate_max_load
from src.result_status import summarize_feeder_result

st.set_page_config(page_title="Electrical Design Checker", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

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
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><div class="eyebrow">Electrical engineering · V0.5</div><h1>⚡ Electrical Design Checker</h1><p>Size a new supply, check an existing circuit, or find the maximum load an existing circuit can support.</p></div>""", unsafe_allow_html=True)

mode = st.radio(
    "What do you want to do?",
    ["Design a supply", "Check an existing supply", "Find maximum load"],
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
    source = st.selectbox("Cable source", ["Generic XLPE/EPR · IEC", "NHXH FE180/E90 · Manufacturer"], key=f"{prefix}source")
    if source.startswith("Generic"):
        material = st.selectbox("Conductor material", ["copper", "aluminium"], key=f"{prefix}mat")
        sizes = [10, 25, 95, 120, 185, 240]
        size = st.selectbox("Phase conductor (mm²)", sizes, key=f"{prefix}size")
        ambient = 30
        grouped = 1
        arrangement = None
        with st.expander("Advanced cable conditions"):
            ambient = st.selectbox("Ambient air temperature (°C)", [20,25,30,35,40,45,50], index=2, key=f"{prefix}amb")
            grouped = st.number_input("Grouped circuits / cables", min_value=1, value=1, step=1, key=f"{prefix}grp")
            if grouped > 1:
                arrangement = st.selectbox("Grouping arrangement", ["bunched", "perforated_tray_single_layer", "ladder_single_layer"], key=f"{prefix}arr")
        cable, route = generic_route(material,size,ambient,grouped,arrangement)
        return source, material, float(size), route, cable
    st.caption("Supported V0 manufacturer condition: copper NHXH FE180/E90, in air, 30 °C. Unsupported corrections remain unverified.")
    construction = st.selectbox("Cable construction", ["5x10", "5x25", "3x95+50", "3x120+70"], key=f"{prefix}const")
    size = get_nhxh_phase_conductor_mm2(construction)
    route = RoutedAmpacityInput(source_kind="manufacturer_nhxh_fe180_e90", construction=construction, ambient_temperature_c=30.0, grouped_circuits=1, parallel_runs=1)
    return source, "copper", float(size), route, None


if mode == "Design a supply":
    st.subheader("Design a supply")
    st.caption("Give the load and installation basics. The tool searches only the cable sizes currently backed by our dataset.")
    with st.sidebar:
        st.caption("DESIGN INPUTS")
        st.header("Load")
        load_kw = st.number_input("Consumer load (kW)", min_value=0.1, value=30.0, step=1.0)
        demand = st.number_input("Usage / demand factor", min_value=0.01, max_value=1.0, value=0.80, step=0.05)
        voltage = st.number_input("System voltage (V)", min_value=1.0, value=400.0, step=10.0)
        pf = st.number_input("Power factor", min_value=0.01, max_value=1.0, value=0.90, step=0.01)
        st.header("Installation")
        material = st.selectbox("Conductor material", ["copper", "aluminium"])
        ambient = 30
        grouped = 1
        arrangement = None
        with st.expander("Advanced cable conditions"):
            ambient = st.selectbox("Ambient air temperature (°C)", [20,25,30,35,40,45,50], index=2)
            grouped = st.number_input("Grouped circuits / cables", min_value=1, value=1, step=1)
            if grouped > 1:
                arrangement = st.selectbox("Grouping arrangement", ["bunched", "perforated_tray_single_layer", "ladder_single_layer"])
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
            r = select_circuit(CircuitSelectionInput(load_type="kw",load_value=load_kw,voltage_v=voltage,phase="three",power_factor=pf,demand_factor=demand,material=material,ambient_temperature_c=ambient,grouped_circuits=grouped,grouping_arrangement=arrangement,length_m=length if check_vd else None,permitted_voltage_drop_percent=vd_limit if check_vd else None,voltage_drop_limit_source=(vd_source.strip() or None) if check_vd else None,allow_annex_g_defaults=annex if check_vd else False))
        except ValueError as exc:
            st.error(str(exc)); st.stop()
        if r.status == "SUGGESTION": st.success("A supported numerical supply suggestion was found.")
        elif r.status == "NO SUPPORTED SOLUTION": st.error("No solution was found inside the current supported dataset.")
        else: st.warning("A complete automatic suggestion is not verified for these inputs.")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Design current · Ib", f"{r.current.design_current_a:.1f} A")
        c2.metric("Suggested breaker", f"{r.suggested_breaker_a:.0f} A" if r.suggested_breaker_a else "—")
        c3.metric("Suggested cable", f"{r.suggested_cable_mm2:g} mm²" if r.suggested_cable_mm2 else "—")
        c4.metric("Cable capacity · Iz", f"{r.cable_iz_a:.1f} A" if r.cable_iz_a else "—")
        c5.metric("Connection", f"{r.suggested_connection.rating_a:.0f} A" if r.suggested_connection and r.suggested_connection.rating_a else "Fixed")
        if r.suggested_connection:
            st.info(f"Suggested connection rating: **{r.suggested_connection.label}**. This is used only as a current-limit recommendation.")
        if r.voltage_drop: st.info(f"Voltage drop: {r.voltage_drop.voltage_drop_percent:.2f}% · {r.voltage_drop.comparison}")
        if r.limitations:
            st.subheader("Important limitations")
            for x in r.limitations: st.warning(x)
        with st.expander("Why this suggestion?"):
            for x in r.trace: st.write("•",x)
            if r.rejected_candidates:
                st.markdown("**Smaller/rejected candidates**")
                for x in r.rejected_candidates: st.write("•",x)
    else:
        st.info("Enter the consumer information in the sidebar, then press **Suggest supply**.")

elif mode == "Find maximum load":
    st.subheader("Find maximum load")
    st.caption("Describe the existing circuit. The lowest supported constraint becomes the limiting current.")
    with st.sidebar:
        st.caption("EXISTING CIRCUIT")
        st.header("Supply")
        voltage = st.number_input("System voltage (V)", min_value=1.0, value=400.0, step=10.0, key="ml_v")
        phase_label = st.selectbox("Phase", ["Three-phase", "Single-phase"], key="ml_phase")
        phase = "three" if phase_label == "Three-phase" else "single"
        pf = st.number_input("Power factor", min_value=0.01, max_value=1.0, value=0.90, step=0.01, key="ml_pf")
        st.header("Known limits")
        use_breaker = st.checkbox("Breaker rating known", value=True)
        breaker = st.number_input("Breaker rating In (A)", min_value=1.0, value=63.0, step=1.0, disabled=not use_breaker)
        use_connection = st.checkbox("Outlet / connection known", value=False)
        connection_option_id = None
        connection = None
        if use_connection:
            connection_mode = st.radio("Connection input", ["Choose connection type", "Enter custom rating"], horizontal=False, key="ml_conn_mode")
            if connection_mode == "Choose connection type":
                options = connection_options_for_phase(phase, include_fixed=True)
                option_labels = {x.label: x.id for x in options}
                selected_label = st.selectbox("Outlet / connection type", list(option_labels.keys()), key="ml_conn_type")
                connection_option_id = option_labels[selected_label]
            else:
                connection = st.number_input("Outlet / connection rating (A)", min_value=1.0, value=32.0, step=1.0)
        use_cable = st.checkbox("Cable known", value=True)
        if use_cable:
            _, material, size, route, _ = source_inputs("ml_")
        else:
            material="copper"; size=None; route=None
        st.header("Voltage drop")
        use_vd = st.checkbox("Use voltage drop as a limit", value=False)
        length = st.number_input("Cable length (m)", min_value=0.1, value=50.0, step=5.0, disabled=not use_vd)
        vd_limit = 5.0
        vd_source = "Project criterion"
        annex = True
        with st.expander("Advanced voltage-drop settings"):
            vd_limit = st.number_input("Maximum permitted drop (%)", min_value=0.1, value=5.0, step=0.5, disabled=not use_vd)
            vd_source = st.text_input("Limit source", value="Project criterion", disabled=not use_vd, key="ml_vds")
            annex = st.checkbox("Use IEC Annex G fallback impedance assumptions", value=True, disabled=not use_vd, key="ml_annex")
    if st.button("Find maximum load", type="primary", use_container_width=True):
        try:
            r=calculate_max_load(MaxLoadInput(voltage_v=voltage,phase=phase,power_factor=pf,breaker_in_a=breaker if use_breaker else None,connection_rating_a=connection if use_connection and connection_option_id is None else None,connection_option_id=connection_option_id if use_connection else None,ampacity_route=route if use_cable else None,length_m=length if use_vd else None,voltage_drop_cross_section_mm2=size if use_vd and use_cable else None,voltage_drop_material=material if use_vd and use_cable else None,permitted_voltage_drop_percent=vd_limit if use_vd else None,voltage_drop_limit_source=(vd_source.strip() or None) if use_vd else None,allow_annex_g_defaults=annex if use_vd else False))
        except ValueError as exc:
            st.error(str(exc)); st.stop()
        if r.status == "RESULT": st.success(f"Limiting factor: {r.limiting_constraint}")
        else: st.warning("A maximum load could not be verified from the supported constraints supplied.")
        c1,c2,c3 = st.columns(3)
        c1.metric("Maximum current", f"{r.max_current_a:.1f} A" if r.max_current_a else "—")
        c2.metric("Maximum active load", f"{r.max_kw:.1f} kW" if r.max_kw else "—")
        c3.metric("Maximum apparent load", f"{r.max_kva:.1f} kVA" if r.max_kva else "—")
        if r.constraints:
            st.subheader("What limits the circuit?")
            for x in sorted(r.constraints,key=lambda z:z.current_a): st.write(f"**{x.name}:** {x.current_a:.1f} A — {x.detail}")
        if r.limitations:
            with st.expander("Limitations / verification status"):
                for x in r.limitations: st.write("•",x)
        with st.expander("Calculation trace"):
            for x in r.trace: st.code(x)
    else:
        st.info("Enter what you know about the existing circuit. You do not need to fill every possible constraint.")

else:
    st.subheader("Check an existing supply")
    st.caption("Check a selected breaker and cable against a known load. This preserves the original feeder-checker workflow.")
    with st.sidebar:
        st.caption("FEEDER INPUTS")
        st.header("Load")
        load_kw=st.number_input("Consumer load (kW)",min_value=0.1,value=97.0,step=1.0,key="ck_load")
        voltage=st.number_input("System voltage (V)",min_value=1.0,value=400.0,step=10.0,key="ck_v")
        pf=st.number_input("Power factor",min_value=0.01,max_value=1.0,value=0.90,step=0.01,key="ck_pf")
        demand=st.number_input("Usage / demand factor",min_value=0.01,max_value=1.0,value=1.0,step=0.05,key="ck_dem")
        st.header("Protection")
        breaker=st.number_input("Breaker rating In (A)",min_value=1.0,value=200.0,step=5.0,key="ck_br")
        st.header("Outlet / connection")
        ck_connection_options = connection_options_for_phase("three")
        ck_connection_labels = ["Not specified"] + [x.label for x in ck_connection_options]
        ck_connection_label = st.selectbox("Connection type", ck_connection_labels, key="ck_conn")
        ck_connection = None if ck_connection_label == "Not specified" else next(x for x in ck_connection_options if x.label == ck_connection_label)
        if ck_connection is not None:
            st.caption("Used as a nominal current limit in the calculation.")
        st.header("Cable")
        _, material, size, route, cable = source_inputs("ck_")
        st.header("Voltage drop")
        use_vd=st.checkbox("Check voltage drop",value=True,key="ck_usevd")
        length=st.number_input("Cable length (m)",min_value=0.1,value=100.0,step=5.0,disabled=not use_vd,key="ck_len")
        vd_limit=5.0; vd_source="Project criterion"; annex=True
        with st.expander("Advanced voltage-drop settings"):
            vd_limit=st.number_input("Maximum permitted drop (%)",min_value=0.1,value=5.0,step=0.5,disabled=not use_vd,key="ck_vdl")
            vd_source=st.text_input("Limit source",value="Project criterion",disabled=not use_vd,key="ck_vds")
            annex=st.checkbox("Use IEC Annex G fallback impedance assumptions",value=True,disabled=not use_vd,key="ck_annex")
    if st.button("Check supply",type="primary",use_container_width=True):
        try:
            r=check_feeder(FeederInput(load_type="kw",load_value=load_kw,voltage_v=voltage,phase="three",power_factor=pf,demand_factor=demand,breaker_in_a=breaker,connection_option_id=ck_connection.id if ck_connection else None,cable=cable,ampacity_route=route,length_m=length if use_vd else None,voltage_drop_cross_section_mm2=size if use_vd else None,voltage_drop_material=material if use_vd else None,permitted_voltage_drop_percent=vd_limit if use_vd else None,voltage_drop_limit_source=(vd_source.strip() or None) if use_vd else None,allow_annex_g_defaults=annex if use_vd else False))
        except ValueError as exc:
            st.error(str(exc)); st.stop()
        summary=summarize_feeder_result(r,voltage_drop_requested=use_vd)
        a,b=st.columns(2); a.metric("Engineering checks",summary.engineering_status); b.metric("Standards verification",summary.standards_status,f"{summary.open_item_count} open item(s)" if summary.open_item_count else None)
        if summary.primary_message:
            (st.error if summary.engineering_status=="FAIL" else st.warning)(summary.primary_message)
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Design current · Ib",f"{r.current.design_current_a:.1f} A")
        c2.metric("Breaker · In",f"{breaker:.0f} A",r.breaker.comparison if r.breaker else None)
        c3.metric("Connection",f"{r.connection.rating_a:.0f} A" if r.connection.rating_a is not None else ("Fixed" if r.connection.option else "—"),r.connection.comparison)
        c4.metric("Cable capacity · Iz",f"{r.ampacity.iz_a:.1f} A" if r.ampacity and r.ampacity.iz_a is not None else "—",r.ampacity_comparison.comparison)
        c5.metric("Voltage drop",f"{r.voltage_drop.voltage_drop_percent:.2f}%" if r.voltage_drop else "—",r.voltage_drop.comparison if r.voltage_drop else None)
        if r.missing_or_unverified:
            with st.expander("Open verification items"):
                for x in r.missing_or_unverified: st.write("•",x)
        with st.expander("Standards, evidence & calculation details"):
            for x in r.verification_summary: st.write("•",x)
            if r.connection.option:
                st.markdown("**Connection check**")
                st.write(r.connection.detail)
                st.write(f"**Evidence status:** {r.connection.option.evidence_status}")
            if r.ampacity and r.ampacity.source_metadata:
                st.markdown("**Cable evidence**")
                for k,v in r.ampacity.source_metadata.items(): st.write(f"**{k.replace('_',' ').capitalize()}:** {v}")
            st.markdown("**Calculation trace**")
            for x in r.current.calculation_trace: st.code(x)
            if r.breaker:
                for x in r.breaker.calculation_trace: st.code(x)
            if r.ampacity:
                for x in r.ampacity.trace: st.code(x)
            if r.voltage_drop:
                for x in r.voltage_drop.trace: st.code(x)
    else:
        st.info("Enter the existing feeder details in the sidebar, then press **Check supply**.")

st.caption("V0.6 keeps the main workflow focused on quantities that affect load, current, protection, cable capacity, voltage drop, or connection current. Secondary assumptions stay under Advanced.")
