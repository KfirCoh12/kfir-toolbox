"""Protection-review workspace backed by the calculated Board Planner hierarchy."""
import streamlit as st

from src.board_persistence import load_last_board, save_last_board
from src.protection_evidence import CoordinationEvidence, FaultEvidence, ProtectiveDeviceEvidence
from src.protection_hierarchy import protection_relationships
from src.protection_summaries import protection_pair_summaries
from src.source_fault import FaultSourceDeclaration, calculate_root_busbar_fault
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

st.markdown("""<div class="hero"><div class="eyebrow">Electrical engineering · Design review</div><h1>🛡️ Protection Checks</h1><p>Review what the Board Planner already knows and add only the protection evidence the project does not yet contain. Planning candidates are context only; they are never treated as proof of protection or selectivity.</p></div>""", unsafe_allow_html=True)


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


def amp_label(value, decimals: int = 0):
    if value is None:
        return "—"
    return f"{value:.{decimals}f} A" if decimals else f"{value:g} A"


def cable_label(mm2, runs):
    if mm2 is None:
        return "—"
    count = runs or 1
    return f"{count} × {mm2:g} mm²" if count > 1 else f"{mm2:g} mm²"


def node_label(graph, node_id: str) -> str:
    node = graph.node_by_id.get(node_id)
    return node.label if node is not None else node_id


def device_label(graph, node_id: str, rating_a: float | None) -> str:
    label = node_label(graph, node_id)
    return label if rating_a is None else f"{label} · {rating_a:g} A"


def rows_from_editor(value):
    if hasattr(value, "to_dict"):
        return value.to_dict("records")
    return list(value)


def root_busbar_pair(graph, relationship) -> bool:
    upstream = graph.node_by_id.get(relationship.upstream_node_id)
    return bool(
        upstream is not None
        and upstream.kind == "incomer"
        and (upstream.board_ref or "").strip() == graph.board_id.strip()
    )


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

# A project-level source declaration can automatically supply the root-busbar fault
# level. It deliberately does not propagate through feeder/final-circuit cables.
saved_fault_source = saved.get("fault_source")
if not isinstance(saved_fault_source, dict):
    saved_fault_source = {}
mode_by_label = {
    "Not declared": "NONE",
    "Known main-board fault level": "DECLARED_BUSBAR",
    "Transformer terminal approximation": "TRANSFORMER_TERMINAL",
}
label_by_mode = {value: key for key, value in mode_by_label.items()}
saved_mode = str(saved_fault_source.get("kind", "NONE"))
if saved_mode not in label_by_mode:
    saved_mode = "NONE"

st.markdown("### Main board fault source")
st.caption("Declare this once for the project. The result applies only at the main board busbar; downstream cable impedance is not guessed.")
with st.expander("Fault source", expanded=saved_mode == "NONE"):
    source_label = st.selectbox(
        "Source basis",
        options=list(mode_by_label),
        index=list(mode_by_label).index(label_by_mode[saved_mode]),
        key="fault_source_mode_v1",
    )
    source_mode = mode_by_label[source_label]
    source_payload = {"kind": source_mode}
    source_result = None

    if source_mode == "DECLARED_BUSBAR":
        c1, c2 = st.columns(2)
        with c1:
            declared_fault = st.number_input(
                "Main board prospective fault current (kA)",
                min_value=0.001,
                value=(float(saved_fault_source["prospective_fault_current_ka"]) if saved_fault_source.get("prospective_fault_current_ka") is not None else None),
                step=0.1,
                format="%.2f",
                key="fault_source_declared_ka_v1",
            )
            source_record = st.text_input(
                "Fault study / source record",
                value=str(saved_fault_source.get("evidence_record_ref", "")),
                placeholder="e.g. utility fault study / approved calculation",
                key="fault_source_record_declared_v1",
            )
        with c2:
            source_rule = st.text_input(
                "Project / calculation basis reference",
                value=str(saved_fault_source.get("rule_basis_ref", "")),
                placeholder="e.g. project protection basis",
                key="fault_source_rule_declared_v1",
            )
        source_payload.update({
            "prospective_fault_current_ka": declared_fault,
            "evidence_record_ref": source_record.strip(),
            "rule_basis_ref": source_rule.strip(),
        })
        if declared_fault is not None and source_record.strip() and source_rule.strip():
            try:
                source_result = calculate_root_busbar_fault(FaultSourceDeclaration(
                    kind="DECLARED_BUSBAR",
                    prospective_fault_current_ka=float(declared_fault),
                    evidence_record_ref=source_record,
                    rule_basis_ref=source_rule,
                ))
            except ValueError as exc:
                st.warning(str(exc))

    elif source_mode == "TRANSFORMER_TERMINAL":
        c1, c2 = st.columns(2)
        with c1:
            transformer_kva = st.number_input(
                "Transformer rated power (kVA)",
                min_value=0.001,
                value=(float(saved_fault_source["transformer_rated_power_kva"]) if saved_fault_source.get("transformer_rated_power_kva") is not None else None),
                step=50.0,
                key="fault_source_tx_kva_v1",
            )
            transformer_uk = st.number_input(
                "Transformer impedance uk (%)",
                min_value=0.001,
                value=(float(saved_fault_source["transformer_impedance_percent"]) if saved_fault_source.get("transformer_impedance_percent") is not None else None),
                step=0.1,
                key="fault_source_tx_uk_v1",
            )
        with c2:
            source_record = st.text_input(
                "Transformer / source record",
                value=str(saved_fault_source.get("evidence_record_ref", "")),
                placeholder="e.g. transformer nameplate / datasheet",
                key="fault_source_record_tx_v1",
            )
            source_rule = st.text_input(
                "Project / calculation basis reference",
                value=str(saved_fault_source.get("rule_basis_ref", "")),
                placeholder="e.g. approved transformer-terminal approximation basis",
                key="fault_source_rule_tx_v1",
            )
        source_payload.update({
            "transformer_rated_power_kva": transformer_kva,
            "transformer_secondary_voltage_v": graph.line_to_line_voltage_v,
            "transformer_impedance_percent": transformer_uk,
            "evidence_record_ref": source_record.strip(),
            "rule_basis_ref": source_rule.strip(),
        })
        st.caption(f"Secondary voltage is taken from Board Planner: {graph.line_to_line_voltage_v:g} V L-L.")
        if transformer_kva is not None and transformer_uk is not None and source_record.strip() and source_rule.strip():
            try:
                source_result = calculate_root_busbar_fault(FaultSourceDeclaration(
                    kind="TRANSFORMER_TERMINAL",
                    transformer_rated_power_kva=float(transformer_kva),
                    transformer_secondary_voltage_v=graph.line_to_line_voltage_v,
                    transformer_impedance_percent=float(transformer_uk),
                    evidence_record_ref=source_record,
                    rule_basis_ref=source_rule,
                ))
            except ValueError as exc:
                st.warning(str(exc))
        st.warning("This is a transformer-terminal approximation, not a full IEC 60909 study. Upstream impedance, motors, parallel sources and downstream cable impedance are outside the result.")

    if source_mode == "NONE":
        source_payload = {"kind": "NONE"}
        source_result = None
        st.caption("No project fault source is declared. Fault kA remains manual for every relationship.")

# Persist the project-level source declaration with the working board so it survives
# reloads and does not need to be re-entered per protective relationship.
if source_payload != saved_fault_source:
    updated_saved = dict(saved)
    updated_saved["fault_source"] = source_payload
    try:
        save_last_board(updated_saved)
        saved = updated_saved
    except OSError as exc:
        st.warning(f"Could not persist fault source settings: {exc}")

if source_result is not None:
    st.success(f"Main board busbar fault level: {source_result.prospective_fault_current_ka:.2f} kA")
    with st.expander("Fault-source calculation basis", expanded=False):
        st.write(source_result.basis)
        st.caption(f"Source record: {source_result.evidence_record_ref} · Basis: {source_result.rule_basis_ref}")

contexts = calculated.context_by_circuit_id
st.markdown("### Protection review")
st.caption("Board Planner values are read-only. Main-busbar fault level is filled from the project source when available; downstream fault levels remain unresolved until cable/network impedance is modeled.")

base_rows = []
auto_fault_by_pair = {}
for relationship in relationships:
    circuit = relationship.downstream_circuit_id or relationship.downstream_node_id
    context = contexts.get(circuit)
    auto_fault = None
    if source_result is not None and root_busbar_pair(graph, relationship):
        auto_fault = source_result.prospective_fault_current_ka
        auto_fault_by_pair[relationship.pair_key] = auto_fault
    base_rows.append({
        "Circuit": circuit,
        "Design current": amp_label(context.design_current_a if context else None, decimals=1),
        "Upstream protection": device_label(graph, relationship.upstream_node_id, relationship.upstream_rating_a),
        "Downstream protection": device_label(graph, relationship.downstream_node_id, relationship.downstream_rating_a),
        "Cable": cable_label(context.cable_mm2, context.cable_runs) if context else "—",
        "Fault kA": auto_fault,
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
        "Upstream protection": st.column_config.TextColumn("Upstream protection", disabled=True),
        "Downstream protection": st.column_config.TextColumn("Downstream protection", disabled=True),
        "Cable": st.column_config.TextColumn("Cable", disabled=True),
        "Fault kA": st.column_config.NumberColumn("Fault kA", min_value=0.001, step=0.1, format="%.2f", help="Prospective fault current at the downstream device. Root-busbar values can be supplied automatically by the project fault source; downstream values are not guessed."),
        "Breaking kA": st.column_config.NumberColumn("Breaking kA", min_value=0.001, step=0.1, format="%.2f", help="Declared breaking capacity of the downstream protective device."),
    },
    key="protection_review_matrix_v4",
)
edited_rows = rows_from_editor(edited)

pair_options = {
    f"{row['Circuit']} · {row['Upstream protection']} → {row['Downstream protection']}": index
    for index, row in enumerate(base_rows)
}
st.markdown("### Relationship details")
selected_label = st.selectbox("Relationship", options=list(pair_options), key="evidence_pair_selector_v4")
selected_index = pair_options[selected_label]
selected_relationship = relationships[selected_index]
selected_auto_fault = auto_fault_by_pair.get(selected_relationship.pair_key)
if selected_auto_fault is not None:
    st.caption(f"Fault level for this relationship comes from the main-board source: {selected_auto_fault:.2f} kA. Editing the table value overrides that value for this session only.")

with st.expander("Advanced traceability", expanded=False):
    st.caption("Breaker-capacity provenance still lives here until a protective-device library supplies it automatically. Project fault-source records are stored once above.")
    c1, c2 = st.columns(2)
    with c1:
        default_rule = source_result.rule_basis_ref if source_result is not None and selected_auto_fault is not None else ""
        rule_ref = st.text_input("Breaking-capacity rule / project basis reference", value=default_rule, key=f"rule_v4_{selected_index}", placeholder="e.g. project protection basis")
        record_ref = st.text_input("Evidence record for the declared numeric comparison", key=f"record_v4_{selected_index}", placeholder="e.g. breaker schedule / datasheet + fault record package")
    with c2:
        downstream_make = st.text_input("Downstream make", key=f"down_make_v4_{selected_index}")
        downstream_model = st.text_input("Downstream model", key=f"down_model_v4_{selected_index}")

st.session_state[f"saved_rule_v4_{selected_index}"] = rule_ref.strip()
st.session_state[f"saved_record_v4_{selected_index}"] = record_ref.strip()
st.session_state[f"saved_down_make_v4_{selected_index}"] = downstream_make.strip()
st.session_state[f"saved_down_model_v4_{selected_index}"] = downstream_model.strip()

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
        make = st.session_state.get(f"saved_down_make_v4_{index}", "")
        model = st.session_state.get(f"saved_down_model_v4_{index}", "")
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
        saved_rule = st.session_state.get(f"saved_rule_v4_{index}", "")
        saved_record = st.session_state.get(f"saved_record_v4_{index}", "")
        if saved_rule:
            rule_refs[pair] = saved_rule
        elif source_result is not None and pair in auto_fault_by_pair:
            rule_refs[pair] = source_result.rule_basis_ref
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

selected_summary = summaries[selected_index]
selected_context = contexts.get(selected_summary.downstream_circuit_id or selected_summary.downstream_node_id)
status_cols = st.columns(4)
status_cols[0].metric("Ib", amp_label(selected_context.design_current_a if selected_context else None, decimals=1))
status_cols[1].metric("Breaker", amp_label(selected_summary.downstream_rating_a))
status_cols[2].metric("Breaking capacity", status_label(selected_summary.breaking_capacity_status))
status_cols[3].metric("Selectivity", status_label(selected_summary.selectivity_status))

with st.expander("Why this status?", expanded=False):
    st.write(selected_summary.breaking_capacity_basis)
    missing = list(selected_summary.breaking_capacity_missing_evidence)
    if missing:
        st.markdown("**Still needed for breaking-capacity verification**")
        for item in missing:
            st.write("•", item)
    if selected_auto_fault is None and source_result is not None:
        st.caption("This relationship is downstream of feeder/circuit impedance. The main-board fault level is intentionally not copied here until that impedance is modeled.")
    st.caption(f"Overall protection: {status_label(selected_summary.protection_status)}. Rating order is never treated as selectivity evidence.")

st.info("Fault-source data is now entered once and reused at the main board busbar. The next reduction in manual input is downstream fault propagation from cable/network impedance, followed by a protective-device library for breaking capacity.")
