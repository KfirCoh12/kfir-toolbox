"""Protection-review workspace backed by the calculated Board Planner hierarchy."""
import streamlit as st

from src.board_persistence import load_last_board, save_last_board
from src.fault_propagation import CableFaultPath
from src.fault_propagation_hierarchy import relationship_fault_contexts
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


def branch_materials_by_circuit(payload: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    branches = payload.get("branches", [])
    if not isinstance(branches, list):
        return result
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        kind = branch.get("kind")
        if kind == "final":
            circuit_id = str(branch.get("circuit_id", "")).strip()
        elif kind in ("field", "sub_board"):
            circuit_id = str(branch.get("feeder_id", "")).strip()
        else:
            continue
        material = str(branch.get("material", "")).strip()
        if circuit_id and material:
            result[circuit_id] = material
    return result


def required_fault_path_circuits(relationships) -> tuple[str, ...]:
    parent_by_device = {item.downstream_node_id: item for item in relationships}
    result: list[str] = []
    for relationship in relationships:
        parent = parent_by_device.get(relationship.upstream_node_id)
        if parent is None or not parent.downstream_circuit_id:
            continue
        circuit_id = parent.downstream_circuit_id
        if circuit_id not in result:
            result.append(circuit_id)
    return tuple(result)


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
st.caption("Declare the electrical source once. Numeric fault calculation and traceability are shown separately so missing references never hide a calculable engineering value.")

source_result = None
source_payload = {"kind": "NONE"}
with st.expander("Fault source", expanded=saved_mode == "NONE"):
    source_label = st.selectbox(
        "Source basis",
        options=list(mode_by_label),
        index=list(mode_by_label).index(label_by_mode[saved_mode]),
        key="fault_source_mode_v3",
    )
    source_mode = mode_by_label[source_label]
    source_payload = {"kind": source_mode}

    if source_mode == "DECLARED_BUSBAR":
        c1, c2 = st.columns(2)
        with c1:
            declared_fault = st.number_input(
                "Main board prospective fault current (kA)",
                min_value=0.001,
                value=(float(saved_fault_source["prospective_fault_current_ka"]) if saved_fault_source.get("prospective_fault_current_ka") is not None else None),
                step=0.1,
                format="%.2f",
                key="fault_source_declared_ka_v3",
            )
            source_record = st.text_input(
                "Fault study / source record",
                value=str(saved_fault_source.get("evidence_record_ref", "")),
                placeholder="e.g. utility fault study / approved calculation",
                key="fault_source_record_declared_v3",
            )
        with c2:
            source_rule = st.text_input(
                "Project / calculation basis reference",
                value=str(saved_fault_source.get("rule_basis_ref", "")),
                placeholder="e.g. project protection basis",
                key="fault_source_rule_declared_v3",
            )
        source_payload.update({
            "prospective_fault_current_ka": declared_fault,
            "evidence_record_ref": source_record.strip(),
            "rule_basis_ref": source_rule.strip(),
        })
        if declared_fault is not None:
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
                key="fault_source_tx_kva_v3",
            )
            transformer_uk = st.number_input(
                "Transformer impedance uk (%)",
                min_value=0.001,
                value=(float(saved_fault_source["transformer_impedance_percent"]) if saved_fault_source.get("transformer_impedance_percent") is not None else None),
                step=0.1,
                key="fault_source_tx_uk_v3",
            )
        with c2:
            source_record = st.text_input(
                "Transformer / source record",
                value=str(saved_fault_source.get("evidence_record_ref", "")),
                placeholder="e.g. transformer nameplate / datasheet",
                key="fault_source_record_tx_v3",
            )
            source_rule = st.text_input(
                "Project / calculation basis reference",
                value=str(saved_fault_source.get("rule_basis_ref", "")),
                placeholder="e.g. approved transformer-terminal approximation basis",
                key="fault_source_rule_tx_v3",
            )
        source_payload.update({
            "transformer_rated_power_kva": transformer_kva,
            "transformer_secondary_voltage_v": graph.line_to_line_voltage_v,
            "transformer_impedance_percent": transformer_uk,
            "evidence_record_ref": source_record.strip(),
            "rule_basis_ref": source_rule.strip(),
        })
        st.caption(f"Secondary voltage is taken from Board Planner: {graph.line_to_line_voltage_v:g} V L-L.")
        if transformer_kva is not None and transformer_uk is not None:
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
        st.warning("This is a transformer-terminal approximation, not a full IEC 60909 study. Upstream impedance, motors and parallel sources remain outside the source result.")

    else:
        source_payload = {"kind": "NONE"}
        st.caption("No project fault source is declared. Fault kA remains manual for every relationship.")

if source_payload != saved_fault_source:
    updated_saved = dict(saved)
    updated_saved["fault_source"] = source_payload
    try:
        save_last_board(updated_saved)
        saved = updated_saved
    except OSError as exc:
        st.warning(f"Could not persist fault source settings: {exc}")

if source_result is not None:
    st.success(f"Calculated main-board busbar fault level: {source_result.prospective_fault_current_ka:.2f} kA")
    if source_result.traceability_complete:
        st.caption("Traceability complete for the project fault-source record.")
    else:
        st.warning(
            "Fault current is calculable, but traceability is incomplete. Add: "
            + "; ".join(source_result.missing_traceability)
            + ". The numeric result can be used as design context, but incomplete traceability will not be promoted to decisive verification evidence."
        )
    with st.expander("Fault-source calculation basis", expanded=False):
        st.write(source_result.basis)
        if source_result.evidence_record_ref:
            st.caption(f"Source record: {source_result.evidence_record_ref}")
        if source_result.rule_basis_ref:
            st.caption(f"Basis: {source_result.rule_basis_ref}")

contexts = calculated.context_by_circuit_id
materials_by_circuit = branch_materials_by_circuit(saved)
path_circuit_ids = required_fault_path_circuits(relationships)
saved_fault_network = saved.get("fault_network")
if not isinstance(saved_fault_network, dict):
    saved_fault_network = {}
saved_lengths = saved_fault_network.get("cable_lengths_m")
if not isinstance(saved_lengths, dict):
    saved_lengths = {}

lengths_by_circuit: dict[str, float] = {}
if path_circuit_ids:
    st.markdown("### Downstream fault paths")
    st.caption("Cable size, parallel runs and material are reused from the board model. Enter each feeder length once; every downstream breaker supplied through that feeder reuses it.")
    with st.expander("Feeder lengths", expanded=any(circuit_id not in saved_lengths for circuit_id in path_circuit_ids)):
        for circuit_id in path_circuit_ids:
            context = contexts.get(circuit_id)
            material = materials_by_circuit.get(circuit_id)
            detail_parts = []
            if context is not None:
                detail_parts.append(cable_label(context.cable_mm2, context.cable_runs))
            if material:
                detail_parts.append(material.title())
            st.markdown(f"**{circuit_id}**" + (" · " + " · ".join(detail_parts) if detail_parts else ""))
            saved_length = saved_lengths.get(circuit_id)
            length_value = float(saved_length) if saved_length is not None else None
            length = st.number_input(
                f"{circuit_id} cable length (m)",
                min_value=0.01,
                value=length_value,
                step=1.0,
                key=f"fault_path_length_v1_{circuit_id}",
                label_visibility="collapsed",
                placeholder="Cable length (m)",
            )
            if length is not None:
                lengths_by_circuit[circuit_id] = float(length)
            if context is None or context.cable_mm2 is None:
                st.caption("Cable size is not available from Board Planner, so this path cannot yet be propagated.")
            elif material not in ("copper", "aluminium"):
                st.caption("Cable material is not available from Board Planner, so this path cannot yet be propagated.")
        st.caption("Screening uses a resistance-only 20 °C conductor model and deliberately omits cable reactance. It is intended to keep breaking-capacity screening on the high-current side, not to replace IEC 60909.")

network_payload = {"cable_lengths_m": lengths_by_circuit}
if network_payload != saved_fault_network:
    updated_saved = dict(saved)
    updated_saved["fault_network"] = network_payload
    try:
        save_last_board(updated_saved)
        saved = updated_saved
    except OSError as exc:
        st.warning(f"Could not persist feeder-length settings: {exc}")

cable_paths: dict[str, CableFaultPath] = {}
for circuit_id, length_m in lengths_by_circuit.items():
    context = contexts.get(circuit_id)
    material = materials_by_circuit.get(circuit_id)
    if (
        context is None
        or context.cable_mm2 is None
        or material not in ("copper", "aluminium")
    ):
        continue
    cable_paths[circuit_id] = CableFaultPath(
        circuit_id=circuit_id,
        material=material,
        cross_section_mm2=context.cable_mm2,
        parallel_runs=context.cable_runs or 1,
        length_m=length_m,
    )

fault_contexts = relationship_fault_contexts(
    graph,
    relationships,
    root_busbar_fault_current_ka=(source_result.prospective_fault_current_ka if source_result is not None else None),
    cable_path_by_circuit_id=cable_paths,
)
fault_context_by_pair = {item.pair_key: item for item in fault_contexts}
auto_fault_by_pair = {
    item.pair_key: item.prospective_fault_current_ka
    for item in fault_contexts
    if item.prospective_fault_current_ka is not None
}

st.markdown("### Protection review")
st.caption("Board values are read-only. Fault kA is filled from the project source and downstream feeder paths when enough data exists; manual edits remain possible for reviewed project values.")

base_rows = []
for relationship in relationships:
    circuit = relationship.downstream_circuit_id or relationship.downstream_node_id
    context = contexts.get(circuit)
    fault_context = fault_context_by_pair[relationship.pair_key]
    if fault_context.prospective_fault_current_ka is not None:
        fault_basis = "Main busbar" if fault_context.path_circuit_id is None else f"Via {fault_context.path_circuit_id}"
    elif fault_context.path_circuit_id:
        fault_basis = f"Needs {fault_context.path_circuit_id} path"
    else:
        fault_basis = "Needs source"
    base_rows.append({
        "Circuit": circuit,
        "Design current": amp_label(context.design_current_a if context else None, decimals=1),
        "Upstream protection": device_label(graph, relationship.upstream_node_id, relationship.upstream_rating_a),
        "Downstream protection": device_label(graph, relationship.downstream_node_id, relationship.downstream_rating_a),
        "Cable": cable_label(context.cable_mm2, context.cable_runs) if context else "—",
        "Fault basis": fault_basis,
        "Fault kA": fault_context.prospective_fault_current_ka,
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
        "Cable": st.column_config.TextColumn("Protected cable", disabled=True),
        "Fault basis": st.column_config.TextColumn("Fault basis", disabled=True),
        "Fault kA": st.column_config.NumberColumn("Fault kA", min_value=0.001, step=0.1, format="%.2f", help="Prospective 3-phase fault current at the downstream protective device. Auto values are screening context and can be overridden by a reviewed project value."),
        "Breaking kA": st.column_config.NumberColumn("Breaking kA", min_value=0.001, step=0.1, format="%.2f", help="Declared breaking capacity of the downstream protective device."),
    },
    key="protection_review_matrix_v6",
)
edited_rows = rows_from_editor(edited)

pair_options = {
    f"{row['Circuit']} · {row['Upstream protection']} → {row['Downstream protection']}": index
    for index, row in enumerate(base_rows)
}
st.markdown("### Relationship details")
selected_label = st.selectbox("Relationship", options=list(pair_options), key="evidence_pair_selector_v6")
selected_index = pair_options[selected_label]
selected_relationship = relationships[selected_index]
selected_fault_context = fault_context_by_pair[selected_relationship.pair_key]
selected_auto_fault = auto_fault_by_pair.get(selected_relationship.pair_key)
if selected_auto_fault is not None:
    if selected_fault_context.path_circuit_id is None:
        st.caption(f"Fault level comes from the main-board source: {selected_auto_fault:.2f} kA.")
    else:
        st.caption(f"Fault level is propagated through {selected_fault_context.path_circuit_id}: {selected_auto_fault:.2f} kA screening value.")
else:
    st.caption(selected_fault_context.basis)

with st.expander("Advanced traceability", expanded=False):
    st.caption("Breaker-capacity provenance still lives here until a protective-device library supplies it automatically. Project fault-source traceability is stored once above.")
    c1, c2 = st.columns(2)
    with c1:
        default_rule = ""
        if source_result is not None and selected_auto_fault is not None and source_result.traceability_complete:
            default_rule = source_result.rule_basis_ref
        rule_ref = st.text_input("Breaking-capacity rule / project basis reference", value=default_rule, key=f"rule_v6_{selected_index}", placeholder="e.g. project protection basis")
        record_ref = st.text_input("Evidence record for the declared numeric comparison", key=f"record_v6_{selected_index}", placeholder="e.g. breaker schedule / datasheet + fault record package")
    with c2:
        downstream_make = st.text_input("Downstream make", key=f"down_make_v6_{selected_index}")
        downstream_model = st.text_input("Downstream model", key=f"down_model_v6_{selected_index}")

st.session_state[f"saved_rule_v6_{selected_index}"] = rule_ref.strip()
st.session_state[f"saved_record_v6_{selected_index}"] = record_ref.strip()
st.session_state[f"saved_down_make_v6_{selected_index}"] = downstream_make.strip()
st.session_state[f"saved_down_model_v6_{selected_index}"] = downstream_model.strip()

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
        make = st.session_state.get(f"saved_down_make_v6_{index}", "")
        model = st.session_state.get(f"saved_down_model_v6_{index}", "")
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
        saved_rule = st.session_state.get(f"saved_rule_v6_{index}", "")
        saved_record = st.session_state.get(f"saved_record_v6_{index}", "")
        if saved_rule:
            rule_refs[pair] = saved_rule
        elif source_result is not None and source_result.traceability_complete and pair in auto_fault_by_pair:
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
    st.markdown("**Fault-current basis**")
    st.write(selected_fault_context.basis)
    if selected_fault_context.missing_inputs:
        st.markdown("**Still needed for automatic fault propagation**")
        for item in selected_fault_context.missing_inputs:
            st.write("•", item)
    missing = list(selected_summary.breaking_capacity_missing_evidence)
    if missing:
        st.markdown("**Still needed for breaking-capacity verification**")
        for item in missing:
            st.write("•", item)
    st.caption(f"Overall protection: {status_label(selected_summary.protection_status)}. Rating order is never treated as selectivity evidence.")

st.info("Main-board fault current can now propagate through known feeder lengths using a conservative resistance-only screening model. The next major reduction in manual input is a protective-device library for breaking capacity and manufacturer evidence.")
