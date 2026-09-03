"""Production HMI workspace for the persisted Board Planner working board."""
from __future__ import annotations

from copy import deepcopy
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from .board_persistence import load_last_board, save_last_board
from .board_planner_state import (
    add_planner_branch,
    planner_owned_payload,
    remove_planner_branch_tree,
)
from .board_review_navigation import branch_uid_for_route_id
from .connection import connection_options_for_phase
from .design_review import DesignReviewSummary, design_review_summary
from .hmi_planner_workspace import (
    _CSS,
    _allowed_additions,
    _branch_label,
    _fmt_a,
    _fmt_cable,
    _fmt_rating,
    _panel_header,
    _route_graph_nodes,
)
from .hmi_single_line import render_hmi_single_line_svg
from .ui_theme import apply_theme
from .working_board_plan import calculate_working_board

_LAYOUT_CSS = r"""
<style>
.bp-tree-note{font-size:.63rem;color:#718aa7;margin:.1rem 0 .45rem}
[data-testid="stExpander"]{border-color:#203650!important;background:#091727!important}
[data-testid="stExpander"] summary p{font-size:.68rem!important;font-weight:650!important;color:#c9ddf3!important}
.bp-schedule-help{font-size:.62rem;color:#6f86a3;margin:-.2rem 0 .35rem}
.bp-diagram-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:1rem 0 .45rem;padding:.55rem .7rem;border:1px solid #213a57;border-radius:8px;background:linear-gradient(90deg,rgba(14,31,51,.98),rgba(9,23,39,.96))}
.bp-diagram-title{font-size:.78rem;font-weight:760;color:#edf6ff;text-transform:uppercase;letter-spacing:.02em}.bp-diagram-sub{font-size:.64rem;color:#718aa7;margin-top:.08rem}.bp-diagram-mode{font-size:.61rem;color:#8fd1ff;border:1px solid rgba(54,167,255,.3);background:rgba(54,167,255,.07);border-radius:5px;padding:.22rem .45rem}
.bp-save-note{font-size:.61rem;color:#78b99b;margin:.35rem 0 0}
.bp-review-detail{border-left:3px solid #f7bf4f;background:rgba(247,191,79,.055);padding:.48rem .62rem;border-radius:0 7px 7px 0}.bp-review-detail strong{font-size:.68rem;color:#e7d29d}.bp-review-detail span{display:block;font-size:.63rem;color:#9d9276;line-height:1.4;margin-top:.12rem}
.bp-review-empty{font-size:.66rem;color:#7895b6;padding:.32rem .05rem .08rem}
.bp-review-note{font-size:.62rem;color:#718aa7;line-height:1.35;padding:.35rem .15rem 0}
.bp-review-inspect{font-size:.61rem;color:#7895b6;text-transform:uppercase;letter-spacing:.08em;font-weight:760;margin:.35rem 0 .25rem}
</style>
"""


def _default_board() -> dict:
    return {
        "board_id": "DB-01",
        "description": "Distribution board",
        "line_to_line_voltage_v": 400.0,
        "line_to_neutral_voltage_v": 230.0,
        "branches": [],
        "uid_counter": 100,
        "selected_node": "busbar",
    }


def _fingerprint(board: dict) -> str:
    return repr(planner_owned_payload(board))


def _persist(board: dict) -> None:
    payload = planner_owned_payload(board)
    save_last_board(payload)
    st.session_state["bp_hmi_source_fingerprint"] = repr(payload)


def _ensure_live_state(saved: dict) -> None:
    fingerprint = _fingerprint(saved)
    if (
        "bp_hmi_board" not in st.session_state
        or st.session_state.get("bp_hmi_source_fingerprint") != fingerprint
    ):
        st.session_state["bp_hmi_board"] = deepcopy(saved)
        st.session_state["bp_hmi_source_fingerprint"] = fingerprint
        st.session_state["bp_hmi_selected_uid"] = "root"
        st.session_state["bp_hmi_focus_circuit_id"] = None
        st.session_state["bp_review_group_code"] = None
        st.session_state["bp_review_issue_key"] = None


def _descendants(branches: list[dict], parent_uid: str) -> list[dict]:
    return [item for item in branches if str(item.get("parent_key", "root")) == parent_uid]


def _selected_branch(board: dict):
    uid = st.session_state.get("bp_hmi_selected_uid", "root")
    return next((item for item in board.get("branches", []) if str(item.get("uid")) == uid), None)


def _select(uid: str) -> None:
    st.session_state["bp_hmi_selected_uid"] = uid
    st.session_state["bp_hmi_focus_circuit_id"] = None
    st.rerun()


def _event_rows(event) -> list[int]:
    try:
        return list(event.selection.rows)
    except (AttributeError, TypeError):
        if isinstance(event, dict):
            return list(event.get("selection", {}).get("rows", []))
    return []


def _review_issue_key(issue) -> str:
    return f"{issue.code}|{issue.target_id}"


def _focus_route(board: dict, route_circuit_id: str | None) -> None:
    route = str(route_circuit_id or "").strip()
    if not route:
        return
    branch_uid = branch_uid_for_route_id(board, route)
    changed = st.session_state.get("bp_hmi_focus_circuit_id") != route
    st.session_state["bp_hmi_focus_circuit_id"] = route
    if branch_uid is not None:
        changed = changed or st.session_state.get("bp_hmi_selected_uid") != branch_uid
        st.session_state["bp_hmi_selected_uid"] = branch_uid
    if changed:
        st.rerun()


def _hierarchy_item(branch: dict, branches: list[dict]) -> None:
    uid = str(branch.get("uid"))
    kind = str(branch.get("kind", "final"))
    children = _descendants(branches, uid)
    selected = uid == st.session_state.get("bp_hmi_selected_uid", "root")
    label = _branch_label(branch).strip()
    if children:
        icon = "◇" if kind == "field" else "▣"
        identity = branch.get("field_id") if kind == "field" else branch.get("sub_board_id")
        with st.expander(f"{icon} {identity or label} · {len(children)} downstream", expanded=selected):
            if st.button(
                f"Select · {label}",
                key=f"bp_tree_select_{uid}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                _select(uid)
            for child in children:
                _hierarchy_item(child, branches)
    elif st.button(
        label,
        key=f"bp_tree_select_{uid}",
        use_container_width=True,
        type="primary" if selected else "secondary",
    ):
        _select(uid)


def _render_hierarchy(board_id: str, branches: list[dict]) -> None:
    _panel_header("Hierarchy", "Collapse groups and select equipment to edit.", "NAVIGATION")
    selected_root = st.session_state.get("bp_hmi_selected_uid", "root") == "root"
    if st.button(
        f"▰ {board_id} · Main board",
        key="bp_tree_select_root",
        use_container_width=True,
        type="primary" if selected_root else "secondary",
    ):
        _select("root")
    st.markdown(
        '<div class="bp-tree-note">Fields and sub-boards expand only when you need their circuits.</div>',
        unsafe_allow_html=True,
    )
    for branch in _descendants(branches, "root"):
        _hierarchy_item(branch, branches)


def _render_schedule(board: dict, calculated) -> None:
    _panel_header("Circuit schedule", "Select one row to trace its complete electrical route.", "LIVE")
    focus = st.session_state.get("bp_hmi_focus_circuit_id")
    schedule = []
    if calculated is not None:
        for context in calculated.circuit_contexts:
            schedule.append(
                {
                    "Focus": "●" if context.circuit_id == focus else "",
                    "Circuit": context.circuit_id,
                    "Ib": _fmt_a(context.design_current_a),
                    "Breaker": _fmt_rating(context.breaker_candidate_a),
                    "Cable": _fmt_cable(context.cable_mm2, context.cable_runs),
                }
            )
    st.markdown(
        '<div class="bp-schedule-help">The active route is marked here whether it was selected from the schedule or Design review.</div>',
        unsafe_allow_html=True,
    )
    event = st.dataframe(
        schedule,
        use_container_width=True,
        hide_index=True,
        height=310,
        on_select="rerun",
        selection_mode="single-row",
        key="bp_hmi_schedule_select",
    )
    rows = _event_rows(event)
    if rows and 0 <= rows[0] < len(schedule):
        _focus_route(board, str(schedule[rows[0]]["Circuit"]))


def _render_review_panel(board: dict, review: DesignReviewSummary) -> None:
    total = len(review.issues)
    badge = f"{review.attention_count} ATTENTION · {review.limitation_count} LIMITATIONS"
    with st.container(border=True):
        _panel_header(
            "Design review",
            "Repeated conditions are grouped. Inspect a group only when you need its affected routes.",
            badge,
        )
        filter_col, clear_col, note_col = st.columns([1.0, 0.9, 4.6], gap="small")
        with filter_col:
            review_filter = st.selectbox(
                "Review filter",
                ["All", "Attention", "Limitations"],
                key="bp_review_filter",
                label_visibility="collapsed",
            )
        with clear_col:
            if st.button("Clear focus", use_container_width=True, key="bp_review_clear"):
                st.session_state["bp_hmi_focus_circuit_id"] = None
                st.session_state["bp_hmi_selected_uid"] = "root"
                st.session_state["bp_review_issue_key"] = None
                st.rerun()
        with note_col:
            st.markdown(
                f'<div class="bp-review-note">{total} target-level items condensed into repeated engineering conditions. Planning/scope only — not protection-verification results.</div>',
                unsafe_allow_html=True,
            )

        visible_groups = [
            group
            for group in review.groups
            if review_filter == "All"
            or (review_filter == "Attention" and group.severity == "ATTENTION")
            or (review_filter == "Limitations" and group.severity == "LIMITATION")
        ]
        if not visible_groups:
            st.markdown(
                '<div class="bp-review-empty">No items in this review filter. Other engineering checks remain separate.</div>',
                unsafe_allow_html=True,
            )
            return

        group_rows = [
            {
                "!": "●" if group.severity == "ATTENTION" else "◇",
                "Issue": group.title,
                "Affected": group.target_count,
                "Scope": group.scope.replace("_", " ").title(),
            }
            for group in visible_groups
        ]
        group_event = st.dataframe(
            group_rows,
            use_container_width=True,
            hide_index=True,
            height=min(170, 46 + 34 * len(group_rows)),
            on_select="rerun",
            selection_mode="single-row",
            key="bp_design_review_group_select",
        )
        group_rows_selected = _event_rows(group_event)
        if group_rows_selected and 0 <= group_rows_selected[0] < len(visible_groups):
            selected_code = visible_groups[group_rows_selected[0]].code
            if st.session_state.get("bp_review_group_code") != selected_code:
                st.session_state["bp_review_group_code"] = selected_code
                st.session_state["bp_review_issue_key"] = None
                st.rerun()

        selected_group = next(
            (
                group
                for group in visible_groups
                if group.code == st.session_state.get("bp_review_group_code")
            ),
            None,
        )
        if selected_group is None:
            return

        st.markdown(
            f'<div class="bp-review-inspect">Inspecting · {escape(selected_group.title)} · {selected_group.target_count} affected</div>',
            unsafe_allow_html=True,
        )
        target_col, detail_col = st.columns([1.25, 2.75], gap="small")
        with target_col:
            focus = st.session_state.get("bp_hmi_focus_circuit_id")
            target_rows = [
                {
                    "Target": issue.target_id,
                    "Route": "●" if issue.route_circuit_id == focus else "",
                }
                for issue in selected_group.issues
            ]
            target_event = st.dataframe(
                target_rows,
                use_container_width=True,
                hide_index=True,
                height=min(190, 46 + 31 * len(target_rows)),
                on_select="rerun",
                selection_mode="single-row",
                key="bp_design_review_target_select",
            )
            target_rows_selected = _event_rows(target_event)
            if target_rows_selected and 0 <= target_rows_selected[0] < len(selected_group.issues):
                issue = selected_group.issues[target_rows_selected[0]]
                issue_key = _review_issue_key(issue)
                st.session_state["bp_review_issue_key"] = issue_key
                _focus_route(board, issue.route_circuit_id)

        with detail_col:
            selected_issue = next(
                (
                    issue
                    for issue in selected_group.issues
                    if _review_issue_key(issue) == st.session_state.get("bp_review_issue_key")
                ),
                None,
            )
            if selected_issue is None:
                detail_title = f"{selected_group.target_count} affected routes"
                detail_text = selected_group.detail
            else:
                detail_title = f"{selected_issue.target_id} · {selected_group.title}"
                detail_text = selected_issue.detail
            st.markdown(
                f'<div class="bp-review-detail"><strong>{escape(detail_title)}</strong><span>{escape(detail_text)}</span></div>',
                unsafe_allow_html=True,
            )


def _apply_and_save(board: dict) -> None:
    _persist(board)
    st.rerun()


def _render_properties(board: dict, calculated) -> None:
    selected = _selected_branch(board)
    board_id = str(board.get("board_id", "Board"))
    description = str(board.get("description", "Distribution board"))
    if selected is None:
        _panel_header("Board properties", "Edit the persisted main-board context.", "INSPECTOR")
        bid = st.text_input("Board ID", value=board_id, key="bp_board_id")
        desc = st.text_input("Description", value=description, key="bp_board_desc")
        v1, v2 = st.columns(2)
        with v1:
            vll = st.number_input(
                "L-L voltage (V)", min_value=1.0, value=float(board.get("line_to_line_voltage_v", 400)), step=10.0, key="bp_vll"
            )
        with v2:
            vln = st.number_input(
                "L-N voltage (V)", min_value=1.0, value=float(board.get("line_to_neutral_voltage_v", 230)), step=10.0, key="bp_vln"
            )
        if st.button("Apply board changes", use_container_width=True, type="primary", key="bp_apply_board"):
            board.update(
                {
                    "board_id": bid.strip() or board_id,
                    "description": desc.strip() or description,
                    "line_to_line_voltage_v": float(vll),
                    "line_to_neutral_voltage_v": float(vln),
                }
            )
            _apply_and_save(board)
        st.markdown('<div class="bp-save-note">Structural changes are autosaved to the working board.</div>', unsafe_allow_html=True)
        return

    kind = str(selected.get("kind", "item"))
    uid = str(selected.get("uid"))
    _panel_header("Properties", "Selected equipment and live design inputs.", kind.replace("_", " ").upper())

    if kind == "final":
        cid = st.text_input("Circuit ID", value=str(selected.get("circuit_id", "")), key=f"bp_cid_{uid}")
        desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"bp_desc_{uid}")
        mode = st.selectbox(
            "Design mode", ["auto", "manual"], index=1 if selected.get("mode") == "manual" else 0,
            format_func=lambda value: "Auto · load based" if value == "auto" else "Manual · connection based", key=f"bp_mode_{uid}"
        )
        phase = st.selectbox(
            "Phase", ["single", "three"], index=0 if selected.get("phase") == "single" else 1,
            format_func=lambda value: "1P" if value == "single" else "3P", key=f"bp_phase_{uid}"
        )
        material = st.selectbox(
            "Conductor", ["copper", "aluminium"], index=1 if selected.get("material") == "aluminium" else 0,
            format_func=lambda value: "Aluminium" if value == "aluminium" else "Copper", key=f"bp_mat_{uid}"
        )
        load_kw = float(selected.get("load_kw", 5.0))
        connection_id = selected.get("connection_option_id")
        if mode == "auto":
            load_kw = st.number_input(
                "Connected load (kW)", min_value=0.1, value=max(0.1, load_kw), step=1.0, key=f"bp_load_{uid}"
            )
            connection_id = None
        else:
            options = connection_options_for_phase(phase)
            option_ids = [item.id for item in options]
            if connection_id not in option_ids:
                connection_id = option_ids[0]
            connection_id = st.selectbox(
                "Connection / outlet",
                option_ids,
                index=option_ids.index(connection_id),
                format_func=lambda value: next(item.label for item in options if item.id == value),
                key=f"bp_connection_{uid}",
            )
        pf = st.number_input(
            "Power factor", min_value=0.01, max_value=1.0, value=float(selected.get("power_factor", 0.9)), step=0.01, key=f"bp_pf_{uid}"
        )
        demand = st.number_input(
            "Demand factor", min_value=0.01, max_value=1.0, value=float(selected.get("demand_factor", 1.0)), step=0.05, key=f"bp_df_{uid}"
        )
        phase_pref = "Auto"
        if phase == "single":
            preferences = ["Auto", "L1", "L2", "L3"]
            current_pref = str(selected.get("phase_preference", "Auto"))
            phase_pref = st.selectbox(
                "Phase preference", preferences, index=preferences.index(current_pref) if current_pref in preferences else 0,
                key=f"bp_phase_pref_{uid}",
            )
        if st.button("Apply circuit changes", use_container_width=True, type="primary", key=f"bp_apply_{uid}"):
            selected.update(
                {
                    "circuit_id": cid.strip() or str(selected.get("circuit_id", "")),
                    "description": desc,
                    "mode": mode,
                    "load_kw": float(load_kw),
                    "phase": phase,
                    "material": material,
                    "power_factor": float(pf),
                    "demand_factor": float(demand),
                    "phase_preference": phase_pref if phase == "single" else "Auto",
                    "connection_option_id": connection_id if mode == "manual" else None,
                }
            )
            _apply_and_save(board)
        if calculated is not None:
            context = calculated.context_by_circuit_id.get(str(selected.get("circuit_id", "")))
            if context is not None:
                st.caption(
                    f"Live: Ib {_fmt_a(context.design_current_a)} · breaker {_fmt_rating(context.breaker_candidate_a)} · cable {_fmt_cable(context.cable_mm2, context.cable_runs)}"
                )

    elif kind == "field":
        feeder = st.text_input("Feeder ID", value=str(selected.get("feeder_id", "")), key=f"bp_feed_{uid}")
        field_id = st.text_input("Field ID", value=str(selected.get("field_id", "")), key=f"bp_field_{uid}")
        desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"bp_fdesc_{uid}")
        material = st.selectbox(
            "Feeder conductor", ["copper", "aluminium"], index=1 if selected.get("material") == "aluminium" else 0,
            format_func=lambda value: "Aluminium" if value == "aluminium" else "Copper", key=f"bp_fmat_{uid}"
        )
        if st.button("Apply field changes", use_container_width=True, type="primary", key=f"bp_apply_{uid}"):
            selected.update(
                {
                    "feeder_id": feeder.strip() or str(selected.get("feeder_id", "")),
                    "field_id": field_id.strip() or str(selected.get("field_id", "")),
                    "description": desc,
                    "material": material,
                }
            )
            _apply_and_save(board)

    else:
        feeder = st.text_input("Feeder ID", value=str(selected.get("feeder_id", "")), key=f"bp_sbfeed_{uid}")
        sub_id = st.text_input("Sub-board ID", value=str(selected.get("sub_board_id", "")), key=f"bp_sbid_{uid}")
        desc = st.text_input("Description", value=str(selected.get("description", "")), key=f"bp_sbdesc_{uid}")
        if st.button("Apply sub-board changes", use_container_width=True, type="primary", key=f"bp_apply_{uid}"):
            selected.update(
                {
                    "feeder_id": feeder.strip() or str(selected.get("feeder_id", "")),
                    "sub_board_id": sub_id.strip() or str(selected.get("sub_board_id", "")),
                    "description": desc,
                }
            )
            _apply_and_save(board)

    st.divider()
    if st.button("Remove selected item", use_container_width=True, key=f"bp_remove_{uid}"):
        remove_planner_branch_tree(board, uid)
        st.session_state["bp_hmi_selected_uid"] = "root"
        st.session_state["bp_hmi_focus_circuit_id"] = None
        _apply_and_save(board)
    st.markdown('<div class="bp-save-note">Applied structural changes are autosaved.</div>', unsafe_allow_html=True)


def render_board_planner() -> None:
    """Render the production Board Planner against the shared persisted working board."""
    apply_theme()
    st.markdown(_CSS + _LAYOUT_CSS, unsafe_allow_html=True)
    try:
        persisted = load_last_board()
    except ValueError as exc:
        st.error(str(exc))
        return
    if persisted is None:
        persisted = _default_board()
        save_last_board(planner_owned_payload(persisted))

    _ensure_live_state(persisted)
    board = st.session_state["bp_hmi_board"]
    branches = board.setdefault("branches", [])
    selected = _selected_branch(board)

    try:
        calculated = calculate_working_board(board)
        graph = calculated.graph
        root_plan = calculated.hierarchy.root.plan
        review = design_review_summary(calculated)
        calculation_error = None
    except (TypeError, ValueError) as exc:
        calculated = None
        graph = None
        root_plan = None
        review = None
        calculation_error = str(exc)

    board_id = str(board.get("board_id", "Board"))
    description = str(board.get("description", "Distribution board"))
    st.markdown(
        f'<div class="bp-topbar"><div class="bp-brand"><div class="bp-brand-mark">◈</div><div><div class="bp-kicker">Electrical distribution · design workstation</div><div class="bp-title">{escape(board_id)} · {escape(description)}</div></div></div><div class="bp-topmeta"><span class="bp-pill live">● AUTOSAVED WORKING BOARD</span><span class="bp-pill">{board.get("line_to_line_voltage_v",400):g} V L-L</span><span class="bp-pill">{len(branches)} branches</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bp-toolbar"><span class="bp-path">Project / Distribution / Board Planner</span><span class="bp-toolbar-note">Shared working board · used by Protection Checks</span></div>',
        unsafe_allow_html=True,
    )

    allowed = _allowed_additions(selected)
    parent_key = "root" if selected is None else str(selected.get("uid"))
    context_name = "Main board" if selected is None else _branch_label(selected).strip()
    st.markdown(
        f'<div class="bp-contextbar"><strong>{"Add downstream of " + escape(context_name) if allowed else "Final circuit selected"}</strong><span>{"Only hierarchy-valid actions are shown" if allowed else "No downstream additions apply"}</span></div>',
        unsafe_allow_html=True,
    )
    action_cols = st.columns([0.8, 0.8, 0.9, 5.0], gap="small")
    if "circuit" in allowed:
        with action_cols[0]:
            if st.button("＋ Circuit", use_container_width=True, type="primary", key="bp_add_circuit"):
                uid = add_planner_branch(board, "circuit", parent_key)
                st.session_state["bp_hmi_selected_uid"] = uid
                st.session_state["bp_hmi_focus_circuit_id"] = None
                _apply_and_save(board)
    if "field" in allowed:
        with action_cols[1]:
            if st.button("＋ Field", use_container_width=True, key="bp_add_field"):
                uid = add_planner_branch(board, "field", parent_key)
                st.session_state["bp_hmi_selected_uid"] = uid
                st.session_state["bp_hmi_focus_circuit_id"] = None
                _apply_and_save(board)
    if "sub_board" in allowed:
        with action_cols[2]:
            if st.button("＋ Sub-board", use_container_width=True, key="bp_add_sub"):
                uid = add_planner_branch(board, "sub_board", parent_key)
                st.session_state["bp_hmi_selected_uid"] = uid
                st.session_state["bp_hmi_focus_circuit_id"] = None
                _apply_and_save(board)

    max_phase = root_plan.phase_balance.max_phase_current_a if root_plan is not None else None
    incomer = root_plan.incomer_candidate.breaker_rating_a if root_plan is not None else None
    circuit_count = len(calculated.circuit_contexts) if calculated is not None else 0
    attention_count = review.attention_count if review is not None else 0
    limitation_count = review.limitation_count if review is not None else 0
    st.markdown(
        f'<div class="bp-kpi-strip"><div class="bp-kpi"><div class="bp-kpi-label">Max phase demand</div><div class="bp-kpi-value">{_fmt_a(max_phase)}</div><div class="bp-kpi-foot">live hierarchy</div></div><div class="bp-kpi"><div class="bp-kpi-label">Incomer candidate</div><div class="bp-kpi-value">{_fmt_rating(incomer)}</div><div class="bp-kpi-foot">planning only</div></div><div class="bp-kpi"><div class="bp-kpi-label">Calculated branches</div><div class="bp-kpi-value">{circuit_count}</div><div class="bp-kpi-foot">feeders + final circuits</div></div><div class="bp-kpi"><div class="bp-kpi-label">Needs attention</div><div class="bp-kpi-value">{attention_count}</div><div class="bp-kpi-foot">{limitation_count} limitations tracked separately</div></div></div>',
        unsafe_allow_html=True,
    )

    if review is not None:
        _render_review_panel(board, review)

    hierarchy_col, schedule_col, properties_col = st.columns([1.0, 1.65, 1.25], gap="small")
    with hierarchy_col:
        with st.container(border=True):
            _render_hierarchy(board_id, branches)
    with schedule_col:
        with st.container(border=True):
            _render_schedule(board, calculated)
    with properties_col:
        with st.container(border=True):
            _render_properties(board, calculated)

    selected = _selected_branch(board)
    focus_circuit_id = st.session_state.get("bp_hmi_focus_circuit_id")
    if focus_circuit_id:
        selection_title = f"Route focus · {focus_circuit_id}"
        selection_sub = "Complete source-to-load route"
        mode = "CIRCUIT FOCUS"
    elif selected is None:
        selection_title = f"{board_id} · {description}"
        selection_sub = "Board overview · downstream groups collapsed"
        mode = "BOARD OVERVIEW"
    else:
        selection_title = _branch_label(selected).strip()
        selection_sub = f"Selected {selected.get('kind','item').replace('_',' ')}"
        mode = "FIELD / EQUIPMENT FOCUS"
    st.markdown(
        f'<div class="bp-diagram-head"><div><div class="bp-diagram-title">Single-line workspace · {escape(selection_title)}</div><div class="bp-diagram-sub">{escape(selection_sub)}</div></div><span class="bp-diagram-mode">{mode}</span></div>',
        unsafe_allow_html=True,
    )
    if calculation_error:
        st.warning(calculation_error)
    elif graph is not None:
        svg = render_hmi_single_line_svg(
            graph,
            selected_node_ids=_route_graph_nodes(graph, selected, focus_circuit_id),
        )
        components.html(
            f'<style>html,body{{margin:0;background:#08131f}}.shell{{height:650px;width:100%;overflow:auto;border:1px solid #1d334d;border-radius:10px;background:#08131f;box-sizing:border-box}}svg{{min-width:100%;min-height:620px}}</style><div class="shell">{svg}</div>',
            height=670,
            scrolling=False,
        )
