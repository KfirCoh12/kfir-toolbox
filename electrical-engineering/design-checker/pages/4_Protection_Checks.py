"""Protection-review workspace backed by the calculated Board Planner hierarchy."""
import streamlit as st

from src.board_persistence import load_last_board
from src.protection_evidence import CoordinationEvidence, FaultEvidence, ProtectiveDeviceEvidence
from src.protection_hierarchy import protection_relationships
from src.protection_summaries import protection_pair_summaries
from src.working_board_plan import calculate_working_board

st.set_page_config(page_title="Protection Checks", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container {max-width: 1500px; padding-top: 1.35rem; padding-bottom: 3rem;}
.hero {padding:.35rem 0 .8rem 0;}
.hero h1 {margin:0; font-size:2.15rem; letter-spacing:-.03em;}
.hero p {margin:.45rem 0 0 0; color:#94a3b8; max-width:1050px;}
.eyebrow {font-size:.72rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.32rem;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-baseweb="input"] > div, [data-baseweb="select"] > div {border-radius:10px !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><div class="eyebrow">Electrical engineering · Design review</div><h1>🛡️ Protection Checks</h1><p>Review what the Board Planner already knows and focus only on missing protection evidence. Planning candidates are shown as context; they are never treated as proof of protection or selectivity.</p></div>""", unsafe_allow_html=True)


def status_label(status: str) -> str:
    return {
        "VERIFIED": "✅ VERIFIED",
        "NOT VERIFIED": "❌ NOT VERIFIED",
        "INSUFFICIENT DATA": "⚠️ NEEDS DATA",
        "NOT CHECKED": "— NOT CHECKED",
    }.get(status, status)


def positive_or_none(value, label: str):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if number <= 0:
        raise ValueError(f"{label} must be greater than 0")
    return number


def amp_label(value):
    return "—" if value is None else f"{value:g} A"


def cable_label(mm2, runs):
    if mm2 is None:
        return "—"
    count = runs or 1
    return f"{count} × {mm2:g} mm²" if count > 1 else f"{mm2:g} mm²"


def node_label(graph, node_id: str) -> str:
    node = graph.node_by_id.get(node_id)
    return node.label if node is not None else node_id


def rows_from_editor(value):
    if hasattr(value, "to_dict"):
        return value.to_dict("records")
    return list(value)


try:
    saved = load_last_board()
except ValueError as exc:
    saved = None
    st.error(str(exc))

if saved is None:
    st.info("No autosaved working board was found. Open Board Planner and create or edit a board first.")
    st.stop()

try:
    calculated = calculate_working_board(saved)
    graph = calculated.graph
    relationships = protection_relationships(graph)
except (TypeError, ValueError) as exc:
    st.error(f"Could not calculate the working board: {exc}")
    st.stop()

board_id = str(saved.get("board_id", "Board"))
board_description = str(saved.get("description", ""))
st.caption(f"Working board: **{board_id}** · {board_description}")

if not relationships:
    st.info("This working board does not yet contain an upstream/downstream protective-device pair to review.")
    st.stop()

contexts = calculated.context_by_circuit_id
st.markdown("### Protection review")
st.caption("Design current, breaker and cable values are imported automatically from Board Planner. Fault level and device breaking capacity remain evidence inputs until those sources are modeled elsewhere in the project.")

base_rows = []
for relationship in relationships:
    circuit = relationship.downstream_circuit_id or relationship.downstream_node_id
    context = contexts.get(circuit)
    base_rows.append({
        "Circuit": circuit,
        "Design current": amp_label(context.design_current_a if context else None),
        "Upstream": node_label(graph, relationship.upstream_node_id),
        "Upstream rating": amp_label(relationship.upstream_rating_a),
        "Downstream": node_label(graph, relationship.downstream_node_id),
        "Downstream rating": amp_label(relationship.downstream_rating_a),
        "Cable": cable_label(context.cable_mm2, context.cable_runs) if context else "—",
        "Fault kA": None,
        "Breaking kA": None,
    })

edited = st.data_editor(
    base_rows,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "Circuit": st.column_config.TextColumn("Circuit", disabled=True),
        "Design current": st.column_config.TextColumn("Ib", disabled=True),
        "Upstream": st.column_config.TextColumn("Upstream", disabled=True),
        "Upstream rating": st.column_config.TextColumn("Upstream A", disabled=True),
        "Downstream": st.column_config.TextColumn("Downstream", disabled=True),
        "Downstream rating": st.column_config.TextColumn("Downstream A", disabled=True),
        "Cable": st.column_config.TextColumn("Cable", disabled=True),
        "Fault kA": st.column_config.NumberColumn("Fault kA", min_value=0.001, step=0.1, format="%.2f", help="Prospective fault current at the downstream device. This is not inferred from breaker size."),
        "Breaking kA": st.column_config.NumberColumn("Breaking kA", min_value=0.001, step=0.1, format="%.2f", help="Declared breaking capacity of the downstream protective device."),
    },
    key="protection_review_matrix_v2",
)
edited_rows = rows_from_editor(edited)

st.markdown("### Evidence details")
pair_options = {
    f"{row['Circuit']} · {row['Upstream']} → {row['Downstream']}": index
    for index, row in enumerate(base_rows)
}
selected_label = st.selectbox("Relationship", options=list(pair_options), key="evidence_pair_selector_v2")
selected_index = pair_options[selected_label]

with st.expander("Advanced traceability", expanded=False):
    st.caption("Only audit/provenance details live here. They do not replace engineering data and will later move to project/device records where possible.")
    c1, c2 = st.columns(2)
    with c1:
        rule_ref = st.text_input("Rule / project basis reference", key=f"rule_v2_{selected_index}", placeholder="e.g. project protection basis")
        record_ref = st.text_input("Evidence record reference", key=f"record_v2_{selected_index}", placeholder="e.g. fault study / calculation record")
    with c2:
        downstream_make = st.text_input("Downstream make", key=f"down_make_v2_{selected_index}")
        downstream_model = st.text_input("Downstream model", key=f"down_model_v2_{selected_index}")

st.session_state[f"saved_rule_v2_{selected_index}"] = rule_ref.strip()
st.session_state[f"saved_record_v2_{selected_index}"] = record_ref.strip()
st.session_state[f"saved_down_make_v2_{selected_index}"] = downstream_make.strip()
st.session_state[f"saved_down_model_v2_{selected_index}"] = downstream_model.strip()

evidence_by_pair = {}
requested_pairs = {relationship.pair_key for relationship in relationships}
rule_refs = {}
record_refs = {}
input_errors = []

for index, (relationship, row) in enumerate(zip(relationships, edited_rows)):
    pair = relationship.pair_key
    try:
        fault_ka = positive_or_none(row.get("Fault kA"), f"{row['Circuit']} fault current")
        breaking_ka = positive_or_none(row.get("Breaking kA"), f"{row['Circuit']} breaking capacity")
        make = st.session_state.get(f"saved_down_make_v2_{index}", "")
        model = st.session_state.get(f"saved_down_model_v2_{index}", "")
        downstream = None
        if any((make, model, breaking_ka is not None)):
            downstream = ProtectiveDeviceEvidence(
                make=make or None,
                model=model or None,
                rating_a=relationship.downstream_rating_a,
                breaking_capacity_ka=breaking_ka,
            )
        evidence_by_pair[pair] = CoordinationEvidence(
            downstream_device=downstream,
            fault=FaultEvidence(prospective_fault_current_ka=fault_ka) if fault_ka is not None else None,
        )
        saved_rule = st.session_state.get(f"saved_rule_v2_{index}", "")
        saved_record = st.session_state.get(f"saved_record_v2_{index}", "")
        if saved_rule:
            rule_refs[pair] = saved_rule
        if saved_record:
            record_refs[pair] = saved_record
    except ValueError as exc:
        input_errors.append(str(exc))

if input_errors:
    for message in input_errors:
        st.error(message)
    st.stop()

summaries = protection_pair_summaries(
    graph,
    evidence_by_pair=evidence_by_pair,
    protection_check_requested=False,
    selectivity_check_requested=False,
    breaking_capacity_requested_pairs=requested_pairs,
    breaking_capacity_rule_basis_ref_by_pair=rule_refs,
    breaking_capacity_evidence_record_ref_by_pair=record_refs,
)

st.markdown("### Review status")
result_rows = []
for summary in summaries:
    circuit = summary.downstream_circuit_id or summary.downstream_node_id
    context = contexts.get(circuit)
    result_rows.append({
        "Circuit": circuit,
        "Ib": amp_label(context.design_current_a if context else None),
        "Breaker": amp_label(summary.downstream_rating_a),
        "Cable": cable_label(context.cable_mm2, context.cable_runs) if context else "—",
        "Breaking capacity": status_label(summary.breaking_capacity_status),
        "Protection": status_label(summary.protection_status),
        "Selectivity": status_label(summary.selectivity_status),
    })
st.dataframe(result_rows, use_container_width=True, hide_index=True)

selected_summary = summaries[selected_index]
with st.expander("Why this status?", expanded=False):
    st.markdown(f"**{selected_label}**")
    st.write(selected_summary.breaking_capacity_basis)
    missing = list(selected_summary.breaking_capacity_missing_evidence)
    if missing:
        st.markdown("**Still needed for breaking-capacity verification**")
        for item in missing:
            st.write("•", item)

st.info("The tool now imports Board Planner sizing automatically. Breaking-capacity verification still needs fault-level and device-capacity evidence; overall protection and selectivity remain separate checks and are not inferred from rating order.")
