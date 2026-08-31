"""Evidence-aware protection checks for the autosaved Board Planner hierarchy."""
import streamlit as st

from src.board_persistence import load_last_board
from src.protection_evidence import (
    CableProtectionEvidence,
    CoordinationEvidence,
    FaultEvidence,
    ProtectiveDeviceEvidence,
)
from src.protection_hierarchy import protection_relationships
from src.protection_summaries import protection_pair_summaries
from src.working_board_graph import graph_from_working_board

st.set_page_config(
    page_title="Protection Checks",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
.block-container {max-width: 1380px; padding-top: 1.4rem; padding-bottom: 3rem;}
.hero {padding:.35rem 0 1rem 0;}
.hero h1 {margin:0; font-size:2.15rem; letter-spacing:-.03em;}
.hero p {margin:.45rem 0 0 0; color:#94a3b8; max-width:900px;}
.eyebrow {font-size:.72rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.32rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #263449; border-radius:14px; padding:.9rem;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-testid="stAlert"] {border-radius:12px;}
[data-baseweb="input"] > div, [data-baseweb="select"] > div {border-radius:10px !important;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="hero"><div class="eyebrow">Electrical engineering · Verification</div><h1>🛡️ Protection Checks</h1><p>Review each real upstream/downstream protective-device pair from the autosaved Board Planner. Breaking-capacity verification is deliberately separate from overall protection and selectivity.</p></div>""",
    unsafe_allow_html=True,
)


def optional_positive_float(value: str, label: str) -> float | None:
    clean = value.strip()
    if not clean:
        return None
    try:
        number = float(clean)
    except ValueError as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if number <= 0:
        raise ValueError(f"{label} must be greater than 0")
    return number


def status_label(status: str) -> str:
    return {
        "VERIFIED": "✅ VERIFIED",
        "NOT VERIFIED": "❌ NOT VERIFIED",
        "INSUFFICIENT DATA": "⚠️ INSUFFICIENT DATA",
        "NOT CHECKED": "— NOT CHECKED",
    }.get(status, status)


try:
    saved = load_last_board()
except ValueError as exc:
    saved = None
    st.error(str(exc))

if saved is None:
    st.info("No autosaved working board was found. Open Board Planner and create or edit a board first.")
    st.stop()

try:
    graph = graph_from_working_board(saved)
    relationships = protection_relationships(graph)
except (TypeError, ValueError) as exc:
    st.error(f"Could not reconstruct the working board: {exc}")
    st.stop()

board_id = str(saved.get("board_id", "Board"))
board_description = str(saved.get("description", ""))
st.caption(f"Working board: **{board_id}** · {board_description}")

if not relationships:
    st.info("This working board does not yet contain an upstream/downstream protective-device pair to check.")
    st.stop()

with st.container(border=True):
    st.markdown("#### Check scope")
    c1, c2 = st.columns(2)
    with c1:
        protection_requested = st.checkbox(
            "Request overall protection evidence review",
            value=False,
            help="This reports evidence readiness only. The current backend does not claim overall protection VERIFIED.",
        )
    with c2:
        selectivity_requested = st.checkbox(
            "Request selectivity evidence review",
            value=False,
            help="This reports evidence readiness only. Breaker rating order never proves selectivity.",
        )
    st.caption(
        "Only the narrow breaking-capacity comparison can currently produce a decisive VERIFIED / NOT VERIFIED result. "
        "Overall protection and selectivity remain separate checks."
    )


evidence_by_pair = {}
requested_pairs = set()
rule_refs = {}
record_refs = {}
input_errors = []

st.markdown("### Protection pairs")
for index, relationship in enumerate(relationships, start=1):
    pair = relationship.pair_key
    circuit_label = relationship.downstream_circuit_id or relationship.downstream_node_id
    title = f"{index}. {circuit_label} · {relationship.upstream_node_id} → {relationship.downstream_node_id}"

    with st.expander(title, expanded=index == 1):
        rating_note = []
        if relationship.upstream_rating_a is not None:
            rating_note.append(f"upstream topology rating {relationship.upstream_rating_a:g} A")
        if relationship.downstream_rating_a is not None:
            rating_note.append(f"downstream topology rating {relationship.downstream_rating_a:g} A")
        if rating_note:
            st.caption("Observed topology only: " + " · ".join(rating_note) + ". These values are not verification evidence by themselves.")

        check_capacity = st.checkbox(
            "Run breaking-capacity check for this pair",
            value=False,
            key=f"pc_request_{index}",
        )
        if check_capacity:
            requested_pairs.add(pair)

        left, right = st.columns(2)
        with left:
            st.markdown("**Fault / downstream device evidence**")
            fault_text = st.text_input(
                "Prospective fault current (kA)",
                value="",
                key=f"pc_fault_{index}",
                placeholder="e.g. 8.5",
            )
            breaking_text = st.text_input(
                "Downstream breaking capacity (kA)",
                value="",
                key=f"pc_breaking_{index}",
                placeholder="e.g. 10",
            )
            rule_ref = st.text_input(
                "Rule / project basis reference",
                value="",
                key=f"pc_rule_{index}",
                placeholder="Required for a decisive breaking-capacity verdict",
            )
            record_ref = st.text_input(
                "Evidence record reference",
                value="",
                key=f"pc_record_{index}",
                placeholder="Fault study, calculation sheet, or other traceable record",
            )

        with right:
            st.markdown("**Device identity**")
            up_make = st.text_input("Upstream make", value="", key=f"pc_up_make_{index}")
            up_model = st.text_input("Upstream model", value="", key=f"pc_up_model_{index}")
            up_rating_text = st.text_input("Upstream rating (A)", value="", key=f"pc_up_rating_{index}")
            down_make = st.text_input("Downstream make", value="", key=f"pc_down_make_{index}")
            down_model = st.text_input("Downstream model", value="", key=f"pc_down_model_{index}")
            down_rating_text = st.text_input("Downstream rating (A)", value="", key=f"pc_down_rating_{index}")

        with st.expander("Additional protection / selectivity evidence"):
            cable_ref = st.text_input("Cable reference", value="", key=f"pc_cable_{index}")
            constraint_ref = st.text_input(
                "Cable protection constraint reference", value="", key=f"pc_constraint_{index}"
            )
            cable_rule_ref = st.text_input(
                "Cable rule-basis reference", value="", key=f"pc_cable_rule_{index}"
            )
            manufacturer_ref = st.text_input(
                "Manufacturer coordination table reference", value="", key=f"pc_mfr_{index}"
            )
            time_current_ref = st.text_input(
                "Verified time-current evidence reference", value="", key=f"pc_tcc_{index}"
            )

        try:
            fault_ka = optional_positive_float(fault_text, "Prospective fault current")
            breaking_ka = optional_positive_float(breaking_text, "Breaking capacity")
            up_rating = optional_positive_float(up_rating_text, "Upstream rating")
            down_rating = optional_positive_float(down_rating_text, "Downstream rating")

            upstream = None
            if any((up_make.strip(), up_model.strip(), up_rating is not None)):
                upstream = ProtectiveDeviceEvidence(
                    make=up_make.strip() or None,
                    model=up_model.strip() or None,
                    rating_a=up_rating,
                )

            downstream = None
            if any((down_make.strip(), down_model.strip(), down_rating is not None, breaking_ka is not None)):
                downstream = ProtectiveDeviceEvidence(
                    make=down_make.strip() or None,
                    model=down_model.strip() or None,
                    rating_a=down_rating,
                    breaking_capacity_ka=breaking_ka,
                )

            cable = None
            if any((cable_ref.strip(), constraint_ref.strip(), cable_rule_ref.strip())):
                cable = CableProtectionEvidence(
                    cable_ref=cable_ref.strip() or None,
                    constraint_ref=constraint_ref.strip() or None,
                    rule_basis_ref=cable_rule_ref.strip() or None,
                )

            evidence_by_pair[pair] = CoordinationEvidence(
                upstream_device=upstream,
                downstream_device=downstream,
                fault=FaultEvidence(prospective_fault_current_ka=fault_ka) if fault_ka is not None else None,
                cable=cable,
                manufacturer_coordination_ref=manufacturer_ref.strip() or None,
                time_current_evidence_ref=time_current_ref.strip() or None,
            )
            if rule_ref.strip():
                rule_refs[pair] = rule_ref.strip()
            if record_ref.strip():
                record_refs[pair] = record_ref.strip()
        except ValueError as exc:
            input_errors.append(f"{circuit_label}: {exc}")

if input_errors:
    for message in input_errors:
        st.error(message)
    st.stop()

try:
    summaries = protection_pair_summaries(
        graph,
        evidence_by_pair=evidence_by_pair,
        protection_check_requested=protection_requested,
        selectivity_check_requested=selectivity_requested,
        breaking_capacity_requested_pairs=requested_pairs,
        breaking_capacity_rule_basis_ref_by_pair=rule_refs,
        breaking_capacity_evidence_record_ref_by_pair=record_refs,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.markdown("### Results")
for index, summary in enumerate(summaries, start=1):
    circuit_label = summary.downstream_circuit_id or summary.downstream_node_id
    with st.container(border=True):
        st.markdown(f"#### {circuit_label}")
        s1, s2, s3 = st.columns(3)
        s1.metric("Overall protection", status_label(summary.protection_status))
        s2.metric("Selectivity", status_label(summary.selectivity_status))
        s3.metric("Breaking capacity", status_label(summary.breaking_capacity_status))

        st.caption(summary.breaking_capacity_basis)
        if summary.breaking_capacity_status in ("VERIFIED", "NOT VERIFIED"):
            st.caption(
                f"Verifier: {summary.breaking_capacity_verifier} {summary.breaking_capacity_verifier_version} · "
                f"Rule basis: {summary.breaking_capacity_rule_basis_ref}"
            )

        missing = []
        if protection_requested:
            missing.extend(f"Protection: {item}" for item in summary.missing_protection_evidence)
        if selectivity_requested:
            missing.extend(f"Selectivity: {item}" for item in summary.missing_selectivity_evidence)
        missing.extend(f"Breaking capacity: {item}" for item in summary.breaking_capacity_missing_evidence)
        if missing:
            with st.expander("Missing / unresolved evidence"):
                for item in dict.fromkeys(missing):
                    st.write("•", item)

st.warning(
    "A VERIFIED breaking-capacity result verifies only the declared numeric breaking-capacity comparison for that pair. "
    "It does not by itself verify overall protection, fault disconnection, cable protection, selectivity, backup protection, or standards compliance."
)
