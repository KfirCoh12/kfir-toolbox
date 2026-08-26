"""Local Streamlit UI for Electrical Design Checker V0."""
import streamlit as st

from src.ampacity_router import RoutedAmpacityInput
from src.cable import CableAmpacityInput
from src.feeder import FeederInput, check_feeder
from src.manufacturer_ampacity import get_nhxh_phase_conductor_mm2
from src.result_status import summarize_feeder_result

st.set_page_config(
    page_title="Electrical Design Checker V0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --panel: rgba(255,255,255,0.035);
        --panel-border: rgba(255,255,255,0.09);
        --muted: rgba(250,250,250,0.68);
        --soft: rgba(250,250,250,0.48);
    }

    .block-container {
        max-width: 1220px;
        padding-top: 2.1rem;
        padding-bottom: 3.5rem;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.4rem;
    }

    [data-testid="stSidebar"] h2 {
        margin-top: 1.35rem;
        margin-bottom: 0.55rem;
        font-size: 1.08rem;
        letter-spacing: 0.01em;
    }

    [data-testid="stSidebar"] label p {
        font-size: 0.91rem;
    }

    [data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input {
        border-radius: 10px !important;
    }

    .hero {
        padding: 1.0rem 0 1.35rem 0;
    }

    .hero h1 {
        margin: 0;
        font-size: 2.45rem;
        line-height: 1.05;
        letter-spacing: -0.035em;
    }

    .hero p {
        margin: 0.65rem 0 0 0;
        color: var(--muted);
        font-size: 1.02rem;
    }

    .eyebrow {
        display: inline-block;
        margin-bottom: 0.55rem;
        color: var(--soft);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.11em;
        text-transform: uppercase;
    }

    .result-card {
        border: 1px solid var(--panel-border);
        border-radius: 14px;
        padding: 1rem 1.05rem 0.95rem 1.05rem;
        background: var(--panel);
        min-height: 112px;
    }

    .result-label {
        color: var(--muted);
        font-size: 0.84rem;
        margin-bottom: 0.35rem;
    }

    .result-value {
        font-size: 2.05rem;
        font-weight: 650;
        letter-spacing: -0.025em;
        line-height: 1.08;
    }

    .status-line {
        margin-top: 0.48rem;
        font-size: 0.84rem;
        color: var(--muted);
    }

    .section-gap {
        height: 0.35rem;
    }

    div.stButton > button {
        min-height: 3rem;
        border-radius: 12px;
        font-weight: 700;
        letter-spacing: 0.01em;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    [data-testid="stExpander"] {
        border-radius: 12px;
        border-color: var(--panel-border);
    }

    .fine-print {
        color: var(--soft);
        font-size: 0.8rem;
        margin-top: 1.15rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Electrical engineering · V0.1</div>
      <h1>⚡ Electrical Design Checker</h1>
      <p>Single-feeder checks with traceable IEC and manufacturer evidence.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.caption("FEEDER INPUTS")

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
        ["Generic XLPE/EPR · IEC", "NHXH FE180/E90 · Manufacturer"],
        help=(
            "Generic values use the supported IEC 60364-5-52 data slice. "
            "NHXH values use a separate manufacturer reference dataset."
        ),
    )

    if cable_source.startswith("Generic"):
        material = st.selectbox("Conductor material", ["copper", "aluminium"])
        cross_section = st.selectbox(
            "Phase conductor (mm²)", [10, 25, 35, 50, 70, 95, 120, 150, 185, 240], index=5
        )
        ambient = st.selectbox(
            "Ambient air temperature (°C)", [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60], index=4
        )
        grouped = st.number_input("Grouped circuits / cables", min_value=1, value=1, step=1)
        arrangement = (
            st.selectbox("Grouping arrangement", ["bunched", "perforated_tray", "ladder"])
            if grouped > 1
            else None
        )
        parallel = st.number_input("Parallel runs", min_value=1, value=1, step=1)
        equal_share = (
            st.checkbox("Equal current sharing confirmed") if parallel > 1 else None
        )
        thdi = st.number_input("THDi (%)", min_value=0.0, value=0.0, step=1.0)
        neutral_loaded = st.checkbox("Neutral is a loaded conductor")
        construction = None
    else:
        st.caption("Supported V0 condition: copper NHXH FE180/E90, in air, 30 °C.")
        construction = st.selectbox("Cable construction", ["5x10", "5x25", "3x95+50", "3x120+70"])
        material = "copper"
        cross_section = get_nhxh_phase_conductor_mm2(construction)
        if cross_section is None:
            st.error("Selected NHXH construction has no verified phase-conductor section.")
            st.stop()
        ambient = 30
        st.text_input("Ambient air temperature", value="30 °C", disabled=True)
        grouped = st.number_input("Grouped circuits / cables", min_value=1, value=1, step=1)
        parallel = st.number_input("Parallel runs", min_value=1, value=1, step=1)
        equal_share = (
            st.checkbox("Equal current sharing confirmed") if parallel > 1 else None
        )
        arrangement = None
        thdi = 0.0
        neutral_loaded = False

    st.header("Voltage drop")
    enable_vd = st.checkbox("Check voltage drop", value=True)
    length_m = st.number_input(
        "Cable length (m)", min_value=0.1, value=100.0, step=5.0, disabled=not enable_vd
    )
    limit_pct = st.number_input(
        "Maximum permitted drop (%)", min_value=0.1, value=5.0, step=0.5, disabled=not enable_vd
    )
    limit_source = st.text_input(
        "Limit source", value="Project criterion", disabled=not enable_vd
    )
    annex_defaults = st.checkbox(
        "Use IEC Annex G fallback impedance assumptions",
        value=True,
        disabled=not enable_vd,
        help="Fallback assumptions are shown explicitly in the calculation details.",
    )

run = st.button("Run feeder check", type="primary", use_container_width=True)

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

    summary = summarize_feeder_result(r, voltage_drop_requested=enable_vd)
    engineering_status = summary.engineering_status
    standards_status = summary.standards_status

    st.subheader("Result")
    s1, s2 = st.columns(2)
    s1.metric("Engineering checks", engineering_status)
    s2.metric(
        "Standards verification",
        standards_status,
        f"{summary.open_item_count} open item(s)" if summary.open_item_count else None,
    )

    if summary.primary_message:
        if summary.engineering_status == "FAIL":
            st.error(summary.primary_message)
        elif summary.standards_status == "INCOMPLETE":
            st.warning(summary.primary_message)
    elif r.overall_outcome == "PASS":
        st.success("All implemented engineering and standards checks passed.")

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    breaker_status = r.breaker.comparison if r.breaker else "Not checked"
    ampacity_status = r.ampacity_comparison.comparison
    vd_status = r.voltage_drop.comparison if r.voltage_drop else "Not checked"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="result-card"><div class="result-label">Design current · Ib</div><div class="result-value">{r.current.design_current_a:.1f} A</div><div class="status-line">Calculated load current</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="result-card"><div class="result-label">Breaker · In</div><div class="result-value">{breaker_a:.0f} A</div><div class="status-line">{summary.breaker_detail}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        iz_text = f"{r.ampacity.iz_a:.1f} A" if r.ampacity and r.ampacity.iz_a is not None else "—"
        st.markdown(
            f'<div class="result-card"><div class="result-label">Cable capacity · Iz</div><div class="result-value">{iz_text}</div><div class="status-line">{summary.cable_detail}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        vd_text = f"{r.voltage_drop.voltage_drop_percent:.2f}%" if r.voltage_drop else "—"
        st.markdown(
            f'<div class="result-card"><div class="result-label">Voltage drop</div><div class="result-value">{vd_text}</div><div class="status-line">{summary.voltage_drop_detail or "Not requested"}</div></div>',
            unsafe_allow_html=True,
        )

    if r.missing_or_unverified:
        with st.expander("Open verification items"):
            for item in r.missing_or_unverified:
                st.write(f"• {item}")

    with st.expander("Standards, evidence & calculation details"):
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

    st.markdown(
        '<div class="fine-print">V0.1 intentionally keeps unsupported conditions unverified instead of estimating them silently.</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Enter a feeder in the sidebar, then run the check. Default values are for demonstration only.")
