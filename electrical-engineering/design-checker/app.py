"""Local Streamlit UI for Electrical Design Checker V0."""
import streamlit as st

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.feeder import FeederInput, check_feeder

NHXH_PHASE_CONDUCTOR_MM2 = {
    "5x10": 10.0,
    "5x25": 25.0,
    "3x95+50": 95.0,
    "3x120+70": 120.0,
}

st.set_page_config(page_title="Electrical Design Checker V0", page_icon="⚡", layout="wide")
st.title("⚡ Electrical Design Checker — V0")
st.caption("Single-feeder design check with traceable IEC and manufacturer evidence.")

with st.sidebar:
    st.header("Load")
    load_kw = st.number_input("Load (kW)", min_value=0.1, value=97.0, step=1.0)
    voltage_v = st.number_input("System voltage (V)", min_value=1.0, value=400.0, step=10.0)
    phase_label = st.selectbox("Phase", ["Three-phase", "Single-phase"])
    phase = "three" if phase_label == "Three-phase" else "single"
    pf = st.number_input("Power factor", min_value=0.01, max_value=1.0, value=0.90, step=0.01)
    demand = st.number_input("Demand factor", min_value=0.01, max_value=1.0, value=1.0, step=0.05)

    st.header("Protection")
    breaker_a = st.number_input("Breaker rating In (A)", min_value=1.0, value=200.0, step=5.0)

    st.header("Cable")
    cable_source = st.selectbox(
        "Cable source",
        ["Generic XLPE/EPR (IEC)", "NHXH FE180/E90 (manufacturer)"],
        help="Generic cable values use the supported IEC 60364-5-52 data slice. NHXH values use a separate manufacturer reference dataset.",
    )

    if cable_source.startswith("Generic"):
        material = st.selectbox("Conductor material", ["copper", "aluminium"])
        cross_section = st.selectbox("Phase conductor (mm²)", [10, 25, 35, 50, 70, 95, 120, 150, 185, 240], index=5)
        ambient = st.selectbox("Ambient air temperature (°C)", [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60], index=4)
        grouped = st.number_input("Grouped circuits/cables", min_value=1, value=1, step=1)
        arrangement = st.selectbox("Grouping arrangement", ["bunched", "perforated_tray", "ladder"]) if grouped > 1 else None
        parallel = st.number_input("Parallel runs", min_value=1, value=1, step=1)
        equal_share = st.checkbox("Equal current sharing confirmed") if parallel > 1 else None
        thdi = st.number_input("THDi (%)", min_value=0.0, value=0.0, step=1.0)
        neutral_loaded = st.checkbox("Neutral is a loaded conductor")
        construction = None
    else:
        st.caption("Supported V0 condition: copper NHXH FE180/E90 in air at 30 °C. Unsupported corrections remain NOT VERIFIED.")
        construction = st.selectbox("Cable construction", ["5x10", "5x25", "3x95+50", "3x120+70"])
        material = "copper"
        cross_section = NHXH_PHASE_CONDUCTOR_MM2[construction]
        ambient = 30
        st.text_input("Ambient air temperature", value="30 °C", disabled=True)
        grouped = st.number_input("Grouped circuits/cables", min_value=1, value=1, step=1)
        parallel = st.number_input("Parallel runs", min_value=1, value=1, step=1)
        equal_share = st.checkbox("Equal current sharing confirmed") if parallel > 1 else None
        arrangement = None
        thdi = 0.0
        neutral_loaded = False

    st.header("Voltage drop")
    enable_vd = st.checkbox("Check voltage drop", value=True)
    length_m = st.number_input("Cable length (m)", min_value=0.1, value=100.0, step=5.0, disabled=not enable_vd)
    limit_pct = st.number_input("Maximum permitted drop (%)", min_value=0.1, value=5.0, step=0.5, disabled=not enable_vd)
    limit_source = st.text_input("Limit source", value="Project criterion", disabled=not enable_vd)
    annex_defaults = st.checkbox(
        "Use IEC Annex G fallback impedance assumptions",
        value=True,
        disabled=not enable_vd,
        help="Fallback assumptions are shown in the calculation trace and are never silent.",
    )

run = st.button("Check feeder", type="primary", use_container_width=True)

if run:
    if cable_source.startswith("Generic"):
        cable = CableAmpacityInput(
            material=material,
            cross_section_mm2=float(cross_section),
            insulation="xlpe_epr",
            loaded_conductors=3 if phase == "three" else 2,
            installation_method="E",
            environment="air",
            ambient_temperature_c=float(ambient),
            grouped_circuits=int(grouped),
            grouping_arrangement=arrangement,
            parallel_runs=int(parallel),
            equal_current_sharing_confirmed=equal_share,
            thdi_percent=float(thdi),
            neutral_loaded=neutral_loaded,
        )
        route = RoutedAmpacityInput(source_kind="iec_generic", generic=cable)
    else:
        cable = None
        route = RoutedAmpacityInput(
            source_kind="manufacturer_nhxh_fe180_e90",
            construction=construction,
            ambient_temperature_c=float(ambient),
            grouped_circuits=int(grouped),
            parallel_runs=int(parallel),
            equal_current_sharing_confirmed=equal_share,
        )

    feeder = FeederInput(
        load_type="kw",
        load_value=float(load_kw),
        voltage_v=float(voltage_v),
        phase=phase,
        power_factor=float(pf),
        demand_factor=float(demand),
        breaker_in_a=float(breaker_a),
        cable=cable,
        ampacity_route=route,
        length_m=float(length_m) if enable_vd else None,
        voltage_drop_cross_section_mm2=float(cross_section) if enable_vd else None,
        voltage_drop_material=material if enable_vd else None,
        permitted_voltage_drop_percent=float(limit_pct) if enable_vd else None,
        voltage_drop_limit_source=limit_source.strip() or None,
        allow_annex_g_defaults=annex_defaults if enable_vd else False,
    )

    try:
        r = check_feeder(feeder)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    comparison_states = [r.breaker.comparison if r.breaker else "NOT VERIFIED", r.ampacity_comparison.comparison]
    if enable_vd:
        comparison_states.append(r.voltage_drop.comparison if r.voltage_drop else "NOT VERIFIED")
    if "FAIL" in comparison_states:
        engineering_status = "FAIL"
    elif any(x in ("NOT VERIFIED", "NO LIMIT CHECKED") for x in comparison_states):
        engineering_status = "INCOMPLETE"
    else:
        engineering_status = "PASS"

    standards_status = "COMPLETE" if r.overall_outcome == "PASS" else "INCOMPLETE"
    s1, s2 = st.columns(2)
    s1.metric("Engineering checks", engineering_status)
    s2.metric("Standards verification", standards_status, f"{len(r.missing_or_unverified)} open item(s)" if r.missing_or_unverified else None)

    if r.missing_or_unverified:
        primary_blocker = r.missing_or_unverified[0]
        if primary_blocker == "breaker protection rule/current IEC basis":
            st.warning("Protection verification is incomplete because the current IEC 60364-4-43 basis has not yet been integrated.")
        else:
            st.warning(f"Verification is incomplete: {primary_blocker}.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Design current Ib", f"{r.current.design_current_a:.1f} A")
    c2.metric("Breaker In", f"{breaker_a:.0f} A", r.breaker.comparison if r.breaker else "Not checked")
    c3.metric("Cable Iz", f"{r.ampacity.iz_a:.1f} A" if r.ampacity and r.ampacity.iz_a is not None else "Not verified", r.ampacity_comparison.comparison)
    c4.metric("Voltage drop", f"{r.voltage_drop.voltage_drop_percent:.2f}%" if r.voltage_drop else "Not checked", r.voltage_drop.comparison if r.voltage_drop else None)

    if r.missing_or_unverified:
        with st.expander("Open verification items"):
            for item in r.missing_or_unverified:
                st.write(f"• {item}")

    with st.expander("Standards, evidence and calculation details"):
        st.markdown("#### Verification status")
        for item in r.verification_summary:
            st.write(f"• {item}")

        if r.ampacity and r.ampacity.source_metadata:
            st.markdown("#### Cable evidence")
            for key, value in r.ampacity.source_metadata.items():
                label = key.replace("_", " ").capitalize()
                st.write(f"**{label}:** {value}")

        st.markdown("#### Calculation trace")
        st.markdown("**Current**")
        for line in r.current.calculation_trace:
            st.code(line)
        if r.breaker:
            st.markdown("**Breaker**")
            for line in r.breaker.calculation_trace:
                st.code(line)
        if r.ampacity:
            st.markdown("**Cable ampacity**")
            for line in r.ampacity.trace:
                st.code(line)
        if r.voltage_drop:
            st.markdown("**Voltage drop**")
            for line in r.voltage_drop.trace:
                st.code(line)

    st.caption("V0 has intentionally narrow evidence coverage. Unsupported conditions remain NOT VERIFIED rather than being approximated silently.")
else:
    st.info("Enter a feeder in the sidebar and press **Check feeder**. The default values are a demonstration case, not a design recommendation.")
