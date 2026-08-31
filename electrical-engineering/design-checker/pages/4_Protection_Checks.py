"""Compact protection-check workspace for the autosaved Board Planner hierarchy."""
import streamlit as st

from src.board_persistence import load_last_board
from src.protection_evidence import CoordinationEvidence, FaultEvidence, ProtectiveDeviceEvidence
from src.protection_hierarchy import protection_relationships
from src.protection_summaries import protection_pair_summaries
from src.working_board_graph import graph_from_working_board

st.set_page_config(page_title="Protection Checks", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container {max-width: 1500px; padding-top: 1.35rem; padding-bottom: 3rem;}
.hero {padding:.35rem 0 .8rem 0;}
.hero h1 {margin:0; font-size:2.15rem; letter-spacing:-.03em;}
.hero p {margin:.45rem 0 0 0; color:#94a3b8; max-width:980px;}
.eyebrow {font-size:.72rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:#64748b; margin-bottom:.32rem;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stExpander"] {border-radius:12px; border-color:#334155;}
[data-baseweb="input"] > div, [data-baseweb="select"] > div {border-radius:10px !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><div class="eyebrow">Electrical engineering · Verification</div><h1>🛡️ Protection Checks</h1><p>Review the board protection hierarchy in one workspace. Each row is one real protective-device relationship; breaking capacity remains separate from overall protection and selectivity.</p></div>""", unsafe_allow_html=True)


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

st.markdown("### Protection relationships")
st.caption("Topology ratings are shown for orientation only. They are not verification evidence and rating order never proves selectivity.")

base_rows = []
for index, relationship in enumerate(relationships, start=1):
    circuit = relationship.downstream_circuit_id or relationship.downstream_node_id
    base_rows.append({
        "Check": False,
        "Circuit": circuit,
        "Upstream": relationship.upstream_node_id,
        "Upstream rating": amp_label(relationship.upstream_rating_a),
        "Downstream": relationship.downstream_node_id,
        "Downstream rating": amp_label(relationship.downstream_rating_a),
        "Fault kA": None,
        "Breaking kA": None,
    })

edited_rows = st.data_editor(
    base_rows,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "Check": st.column_config.CheckboxColumn("Check", help="Explicitly request the narrow breaking-capacity comparison for this relationship."),
        "Circuit": st.column_config.TextColumn("Circuit", disabled=True),
        "Upstream": st.column_config.TextColumn("Upstream", disabled=True),
        "Upstream rating": st.column_config.TextColumn("Upstream A", disabled=True),
        "Downstream": st.column_config.TextColumn("Downstream", disabled=True),
        "Downstream rating": st.column_config.TextColumn("Downstream A", disabled=True),
        "Fault kA": st.column_config.NumberColumn("Fault kA", min_value=0.001, step=0.1, format="%.2f", help="Declared prospective fault current."),
        "Breaking kA": st.column_config.NumberColumn("Breaking kA", min_value=0.001, step=0.1, format="%.2f", help="Declared downstream breaking capacity."),
    },
    key="protection_matrix",
)

st.markdown("### Evidence details")
pair_options = {
    f"{row['Circuit']} · {row['Upstream']} → {row['Downstream']}": index
    for index, row in enumerate(base_rows)
}
selected_label = st.selectbox("Relationship to edit", options=list(pair_options), key="evidence_pair_selector")
selected_index = pair_options[selected_label]
selected_relationship = relationships[selected_index]
selected_pair = selected_relationship.pair_key

with st.expander("Traceability and advanced evidence", expanded=False):
    st.caption("These fields apply only to the selected relationship. Keep the main table compact; open this panel when a check needs traceable evidence or broader protection/selectivity review.")
    c1, c2 = st.columns(2)
    with c1:
        rule_ref = st.text_input("Rule / project basis reference", key=f"rule_{selected_index}", placeholder="Required for a decisive breaking-capacity verdict")
        record_ref = st.text_input("Evidence record reference", key=f"record_{selected_index}", placeholder="Fault study, calculation sheet, or other traceable record")
    with c2:
        downstream_make = st.text_input("Downstream make", key=f"down_make_{selected_index}")
        downstream_model = st.text_input("Downstream model", key=f"down_model_{selected_index}")

    st.divider()
    protection_requested = st.checkbox("Request overall protection evidence review", value=False, key=f"protection_request_{selected_index}", help="Evidence readiness only; this does not claim overall protection VERIFIED.")
    selectivity_requested = st.checkbox("Request selectivity evidence review", value=False, key=f"selectivity_request_{selected_index}", help="Breaker rating order never proves selectivity.")
    if protection_requested or selectivity_requested:
        st.info("Detailed cable-protection and coordination evidence entry will be added here next. Until then these broader checks remain conservative and cannot self-promote to VERIFIED.")

# Per-pair traceability lives in session state even when another row is selected.
evidence_by_pair = {}
requested_pairs = set()
rule_refs = {}
record_refs = {}
input_errors = []

# Store current selected detail values before evaluating every row.
st.session_state[f"saved_rule_{selected_index}"] = rule_ref.strip()
st.session_state[f"saved_record_{selected_index}"] = record_ref.strip()
st.session_state[f"saved_down_make_{selected_index}"] = downstream_make.strip()
st.session_state[f"saved_down_model_{selected_index}"] = downstream_model.strip()

for index, (relationship, row) in enumerate(zip(relationships, edited_rows)):
    pair = relationship.pair_key
    try:
        fault_ka = positive_or_none(row.get("Fault kA"), f"{row['Circuit']} fault current")
        breaking_ka = positive_or_none(row.get("Breaking kA"), f"{row['Circuit']} breaking capacity")
        if bool(row.get("Check")):
            requested_pairs.add(pair)

        make = st.session_state.get(f"saved_down_make_{index}", "")
        model = st.session_state.get(f"saved_down_model_{index}", "")
        downstream = None
        if any((make, model, breaking_ka is not None)):
            downstream = ProtectiveDeviceEvidence(make=make or None, model=model or None, breaking_capacity_ka=breaking_ka)
        evidence_by_pair[pair] = CoordinationEvidence(
            downstream_device=downstream,
            fault=FaultEvidence(prospective_fault_current_ka=fault_ka) if fault_ka is not None else None,
        )
        saved_rule = st.session_state.get(f"saved_rule_{index}", "")
        saved_record = st.session_state.get(f"saved_record_{index}", "")
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

# Broad evidence requests are intentionally not promoted from a selected-row UI toggle to all pairs.
# The current summary API scopes these globally, so keep them false until per-pair broader-check support exists.
summaries = protection_pair_summaries(
    graph,
    evidence_by_pair=evidence_by_pair,
    protection_check_requested=False,
    selectivity_check_requested=False,
    breaking_capacity_requested_pairs=requested_pairs,
    breaking_capacity_rule_basis_ref_by_pair=rule_refs,
    breaking_capacity_evidence_record_ref_by_pair=record_refs,
)

st.markdown("### Check results")
result_rows = []
for summary in summaries:
    circuit = summary.downstream_circuit_id or summary.downstream_node_id
    result_rows.append({
        "Circuit": circuit,
        "Upstream": summary.upstream_node_id,
        "Downstream": summary.downstream_node_id,
        "Protection": status_label(summary.protection_status),
        "Selectivity": status_label(summary.selectivity_status),
        "Breaking capacity": status_label(summary.breaking_capacity_status),
    })

st.dataframe(result_rows, use_container_width=True, hide_index=True)

selected_summary = summaries[selected_index]
with st.expander("Selected relationship result details", expanded=False):
    st.markdown(f"**{selected_label}**")
    st.write(selected_summary.breaking_capacity_basis)
    if selected_summary.breaking_capacity_status in ("VERIFIED", "NOT VERIFIED"):
        st.caption(f"Verifier: {selected_summary.breaking_capacity_verifier} {selected_summary.breaking_capacity_verifier_version} · Rule basis: {selected_summary.breaking_capacity_rule_basis_ref}")
    missing = list(selected_summary.breaking_capacity_missing_evidence)
    if missing:
        st.markdown("**Missing / unresolved breaking-capacity evidence**")
        for item in missing:
            st.write("•", item)

st.warning("A VERIFIED breaking-capacity result verifies only the declared numeric comparison for that relationship. It does not by itself verify overall protection, fault disconnection, cable protection, selectivity, backup protection, or standards compliance.")
