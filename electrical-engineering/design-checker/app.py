"""Local Streamlit UI for Electrical Design Checker V0."""
import streamlit as st
from src.cable import CableAmpacityInput
from src.ampacity_router import RoutedAmpacityInput
from src.feeder import FeederInput, check_feeder

st.set_page_config(page_title="Electrical Design Checker V0", page_icon="⚡", layout="wide")
st.title("⚡ Electrical Design Checker — V0")
st.caption("Single-feeder checker with explicit IEC/manufacturer evidence routing. NOT VERIFIED is not a pass.")

with st.sidebar:
    st.header("Load")
    load_kw=st.number_input("Load (kW)",min_value=0.1,value=97.0,step=1.0)
    voltage_v=st.number_input("System voltage (V)",min_value=1.0,value=400.0,step=10.0)
    phase_label=st.selectbox("Phase",["Three-phase","Single-phase"]); phase="three" if phase_label=="Three-phase" else "single"
    pf=st.number_input("Power factor",min_value=0.01,max_value=1.0,value=0.90,step=0.01)
    demand=st.number_input("Demand factor",min_value=0.01,max_value=1.0,value=1.0,step=0.05)
    st.header("Protection")
    breaker_a=st.number_input("Selected breaker In (A)",min_value=1.0,value=200.0,step=5.0)
    st.header("Cable")
    cable_family=st.selectbox("Cable data source",["Generic IEC XLPE/EPR","NHXH FE180/E90 — manufacturer reference"],help="Manufacturer values remain separate from IEC 60364 table data.")
    if cable_family.startswith("Generic"):
        material=st.selectbox("Conductor",["copper","aluminium"])
        cross_section=st.selectbox("Cross-section (mm²)",[10,25,35,50,70,95,120,150,185,240],index=5)
        ambient=st.selectbox("Ambient air temperature (°C)",[10,15,20,25,30,35,40,45,50,55,60],index=4)
        grouped=st.number_input("Grouped circuits/cables",min_value=1,value=1,step=1)
        arrangement=st.selectbox("Grouping arrangement",["bunched","perforated_tray","ladder"]) if grouped>1 else None
        parallel=st.number_input("Parallel runs",min_value=1,value=1,step=1)
        equal_share=st.checkbox("Acceptable/equal current sharing confirmed") if parallel>1 else None
        thdi=st.number_input("THDi (%)",min_value=0.0,value=0.0,step=1.0)
        neutral_loaded=st.checkbox("Neutral treated as loaded conductor")
    else:
        st.info("V0 manufacturer slice: NHXH FE180/E90 copper cable, in air, 30 °C. Unsupported corrections stay NOT VERIFIED.")
        construction=st.selectbox("Exact construction",["5x10","5x25","3x95+50","3x120+70"])
        ambient=st.selectbox("Ambient air temperature (°C)",[30],index=0)
        grouped=st.number_input("Grouped circuits/cables",min_value=1,value=1,step=1)
        parallel=st.number_input("Parallel runs",min_value=1,value=1,step=1)
        equal_share=st.checkbox("Acceptable/equal current sharing confirmed") if parallel>1 else None
        material="copper"; cross_section=float(''.join(ch for ch in construction.split('x')[1] if ch.isdigit()).split('+')[0]) if 'x' in construction else 0
    st.header("Voltage drop")
    enable_vd=st.checkbox("Check voltage drop",value=True)
    length_m=st.number_input("Length (m)",min_value=0.1,value=100.0,step=5.0,disabled=not enable_vd)
    limit_pct=st.number_input("Permitted drop (%)",min_value=0.1,value=5.0,step=0.5,disabled=not enable_vd)
    limit_source=st.text_input("Limit source",value="Project criterion",disabled=not enable_vd)
    annex_defaults=st.checkbox("Allow IEC 60364-5-52 Annex G fallback impedance assumptions",value=True,disabled=not enable_vd)

run=st.button("Check feeder",type="primary",use_container_width=True)
if run:
    if cable_family.startswith("Generic"):
        cable=CableAmpacityInput(material=material,cross_section_mm2=float(cross_section),insulation="xlpe_epr",loaded_conductors=3 if phase=="three" else 2,installation_method="E",environment="air",ambient_temperature_c=float(ambient),grouped_circuits=int(grouped),grouping_arrangement=arrangement,parallel_runs=int(parallel),equal_current_sharing_confirmed=equal_share,thdi_percent=float(thdi),neutral_loaded=neutral_loaded)
        route=RoutedAmpacityInput(source_kind="iec_generic",generic=cable)
    else:
        cable=None
        route=RoutedAmpacityInput(source_kind="manufacturer_nhxh_fe180_e90",construction=construction,ambient_temperature_c=float(ambient),grouped_circuits=int(grouped),parallel_runs=int(parallel),equal_current_sharing_confirmed=equal_share)
    feeder=FeederInput(load_type="kw",load_value=float(load_kw),voltage_v=float(voltage_v),phase=phase,power_factor=float(pf),demand_factor=float(demand),breaker_in_a=float(breaker_a),cable=cable,ampacity_route=route,length_m=float(length_m) if enable_vd else None,voltage_drop_cross_section_mm2=float(cross_section) if enable_vd else None,voltage_drop_material=material if enable_vd else None,permitted_voltage_drop_percent=float(limit_pct) if enable_vd else None,voltage_drop_limit_source=limit_source.strip() or None,allow_annex_g_defaults=annex_defaults if enable_vd else False)
    try: r=check_feeder(feeder)
    except ValueError as exc: st.error(str(exc)); st.stop()
    icon={"PASS":"✅","FAIL":"❌","NOT VERIFIED":"⚠️"}.get(r.overall_outcome,"ℹ️")
    st.header(f"{icon} Overall: {r.overall_outcome}")
    if r.overall_outcome=="NOT VERIFIED": st.warning("One or more engineering/standards checks are incomplete or not currently verified. This is not an approval of the feeder.")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Design current Ib",f"{r.current.design_current_a:.1f} A")
    c2.metric("Breaker In",f"{breaker_a:.0f} A",r.breaker.comparison if r.breaker else "Not checked")
    c3.metric("Cable Iz",f"{r.ampacity.iz_a:.1f} A" if r.ampacity and r.ampacity.iz_a is not None else "Not verified",r.ampacity_comparison.comparison)
    c4.metric("Voltage drop",f"{r.voltage_drop.voltage_drop_percent:.2f}%" if r.voltage_drop else "Not checked",r.voltage_drop.comparison if r.voltage_drop else None)
    if r.ampacity and r.ampacity.source_metadata:
        with st.expander("Cable evidence / provenance"):
            for k,v in r.ampacity.source_metadata.items(): st.write(f"**{k}:** {v}")
    st.subheader("Verification summary")
    for item in r.verification_summary: st.write("•",item)
    if r.missing_or_unverified:
        st.subheader("Missing / unsupported")
        for item in r.missing_or_unverified: st.warning(item)
    with st.expander("Calculation trace"):
        st.markdown("**Current**"); [st.code(x) for x in r.current.calculation_trace]
        if r.breaker: st.markdown("**Breaker**"); [st.code(x) for x in r.breaker.calculation_trace]
        if r.ampacity: st.markdown("**Cable ampacity**"); [st.code(x) for x in r.ampacity.trace]
        if r.voltage_drop: st.markdown("**Voltage drop**"); [st.code(x) for x in r.voltage_drop.trace]
    st.caption("V0 scope is intentionally narrow. Generic ampacity uses the explicitly supported IEC 60364-5-52 slice; NHXH FE180/E90 uses a separate manufacturer reference layer. Current IEC 60364-4-43 verification is not yet implemented.")
else:
    st.info("Enter a feeder in the sidebar and press **Check feeder**. Defaults are a demonstration case, not a design recommendation.")
