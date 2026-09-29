"""Embedded AI collaboration workspace for Board Planner."""
from __future__ import annotations

import streamlit as st

from src.ai_planner_assistant import (
    api_key_configured,
    configured_model,
    run_assistant_turn,
)
from src.planner_bridge import get_project
from src.ui_theme import apply_theme
from src.working_board_baseline import ensure_office_working_baseline

st.set_page_config(
    page_title="AI Board Assistant",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_theme()
ensure_office_working_baseline()

st.markdown(
    """
<style>
.block-container{max-width:1780px;padding-top:1.55rem!important;padding-bottom:2.2rem}
.ai-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.7rem .85rem;margin:.1rem 0 .65rem;background:linear-gradient(180deg,rgba(19,34,56,.98),rgba(12,25,43,.98));border:1px solid #2b4362;border-radius:11px}
.ai-kicker{font-size:.61rem;color:#7b94b3;letter-spacing:.13em;text-transform:uppercase;font-weight:800}
.ai-title{font-size:1.08rem;color:#f4f8ff;font-weight:740;margin-top:.08rem}
.ai-sub{font-size:.66rem;color:#7895b6;margin-top:.15rem}
.ai-pill{font-size:.62rem;color:#8fd1ff;border:1px solid rgba(54,167,255,.28);background:rgba(54,167,255,.07);padding:.24rem .48rem;border-radius:6px;white-space:nowrap}
.ai-note{font-size:.65rem;color:#7895b6;line-height:1.45;margin:.2rem 0 .65rem}
.ai-section{font-size:.63rem;color:#718aa7;text-transform:uppercase;letter-spacing:.08em;font-weight:780;margin:.45rem 0 .3rem}
.ai-proposal{border-left:3px solid #36a7ff;background:rgba(54,167,255,.055);padding:.48rem .6rem;border-radius:0 7px 7px 0;margin:.35rem 0}
.ai-proposal strong{font-size:.68rem;color:#cce9ff}.ai-proposal span{display:block;font-size:.62rem;color:#7895b6;margin-top:.1rem}
[data-testid="stChatMessage"]{background:#091727;border:1px solid #1d334d;border-radius:8px;padding:.15rem .45rem}
[data-testid="stTextArea"] textarea{background:#081523!important;border-color:#243d5a!important}
</style>
""",
    unsafe_allow_html=True,
)

model = configured_model()
st.markdown(
    f'<div class="ai-head"><div><div class="ai-kicker">Electrical distribution · shared design workspace</div><div class="ai-title">◆ AI Board Assistant</div><div class="ai-sub">Discuss the project here. Board changes are created as reviewable proposals.</div></div><span class="ai-pill">{model}</span></div>',
    unsafe_allow_html=True,
)

if not api_key_configured():
    st.error(
        "OPENAI_API_KEY is not available to the running service yet. "
        "Add/seal it in Railway Variables and redeploy the service."
    )
    st.stop()

try:
    snapshot = get_project()
except (OSError, TypeError, ValueError) as exc:
    st.error(f"Could not read the working project: {exc}")
    st.stop()

if "ai_board_messages" not in st.session_state:
    st.session_state["ai_board_messages"] = []
if "ai_board_previous_response_id" not in st.session_state:
    st.session_state["ai_board_previous_response_id"] = None
if "ai_board_last_usage" not in st.session_state:
    st.session_state["ai_board_last_usage"] = None

top_left, top_right = st.columns([4.9, 1.1], gap="small")
with top_left:
    st.markdown(
        '<div class="ai-note">The assistant can read the current Planner state, remember supplied facts, track missing information, and create proposals. It cannot directly approve its own board changes.</div>',
        unsafe_allow_html=True,
    )
with top_right:
    if st.button("New chat", use_container_width=True, key="ai_new_chat"):
        st.session_state["ai_board_messages"] = []
        st.session_state["ai_board_previous_response_id"] = None
        st.session_state["ai_board_last_usage"] = None
        st.rerun()

chat_col, state_col = st.columns([1.7, 1.0], gap="small")

with chat_col:
    st.markdown('<div class="ai-section">Conversation</div>', unsafe_allow_html=True)
    with st.container(height=505, border=True):
        if not st.session_state["ai_board_messages"]:
            with st.chat_message("assistant"):
                st.markdown(
                    "Tell me what board you need to design and give me whatever information "
                    "you already have. I’ll work from the current Planner state, identify what "
                    "is missing, and create reviewable board proposals when there is enough information."
                )
        for message in st.session_state["ai_board_messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    with st.form("ai_board_prompt_form", clear_on_submit=True):
        prompt = st.text_area(
            "Message",
            height=95,
            placeholder=(
                "Example: This is a 700 m² office for about 150 people. "
                "The board has a 400 A supply. Start a preliminary concept."
            ),
            label_visibility="collapsed",
        )
        send = st.form_submit_button(
            "Send to Board Assistant",
            type="primary",
            use_container_width=True,
        )

    if send:
        user_text = str(prompt).strip()
        if not user_text:
            st.warning("Enter a message first.")
        else:
            st.session_state["ai_board_messages"].append(
                {"role": "user", "content": user_text}
            )
            try:
                with st.spinner("Reviewing the current project and Planner..."):
                    result = run_assistant_turn(
                        user_text,
                        previous_response_id=st.session_state[
                            "ai_board_previous_response_id"
                        ],
                    )
            except Exception as exc:
                # Avoid printing environment details or secrets. API/Planner exceptions are
                # reduced to their public message only.
                st.session_state["ai_board_messages"].append(
                    {
                        "role": "assistant",
                        "content": f"I couldn't complete that turn: {exc}",
                    }
                )
            else:
                st.session_state["ai_board_messages"].append(
                    {"role": "assistant", "content": result.text}
                )
                st.session_state["ai_board_previous_response_id"] = result.response_id
                st.session_state["ai_board_last_usage"] = {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "tool_calls": list(result.tool_calls),
                }
            st.rerun()

with state_col:
    st.markdown('<div class="ai-section">Live project</div>', unsafe_allow_html=True)
    revision = snapshot["revision"]
    board = snapshot["board"]
    review = snapshot["review"]
    branches = board.get("branches", [])
    k1, k2 = st.columns(2)
    k1.metric("Revision", revision)
    k2.metric("Branches", len(branches) if isinstance(branches, list) else 0)
    k3, k4 = st.columns(2)
    k3.metric("Attention", review.get("attention_count", 0))
    k4.metric("Limitations", review.get("limitation_count", 0))

    st.page_link(
        "pages/3_Board_Planner.py",
        label="Open Board Planner",
        icon="◈",
        use_container_width=True,
    )

    open_questions = snapshot.get("open_questions", [])
    st.markdown(
        f'<div class="ai-section">Open questions · {len(open_questions)}</div>',
        unsafe_allow_html=True,
    )
    if open_questions:
        for item in open_questions[:8]:
            st.markdown(
                f"**{item['priority'].replace('_', ' ').title()}** · {item['prompt']}"
            )
    else:
        st.caption("No stored project questions.")

    pending = snapshot.get("pending_proposals", [])
    st.markdown(
        f'<div class="ai-section">Pending proposals · {len(pending)}</div>',
        unsafe_allow_html=True,
    )
    if pending:
        for proposal in pending[:5]:
            st.markdown(
                f'<div class="ai-proposal"><strong>{proposal["proposal_id"]} · {proposal["title"]}</strong><span>{proposal["reason"]}</span></div>',
                unsafe_allow_html=True,
            )
        st.caption("Review, recalculate, apply or reject these in Board Planner.")
    else:
        st.caption("No proposal is waiting for review.")

    facts = snapshot.get("facts", {})
    st.markdown(
        f'<div class="ai-section">Project facts · {len(facts)}</div>',
        unsafe_allow_html=True,
    )
    if facts:
        fact_rows = []
        for key, fact in list(facts.items())[:12]:
            value = str(fact.get("value"))
            if len(value) > 45:
                value = value[:42] + "..."
            fact_rows.append(
                {
                    "Fact": key,
                    "Value": value,
                    "Basis": str(fact.get("provenance", "")).replace("_", " ").title(),
                }
            )
        st.dataframe(
            fact_rows,
            use_container_width=True,
            hide_index=True,
            height=min(235, 44 + 31 * len(fact_rows)),
        )
    else:
        st.caption("Facts supplied in chat will appear here.")

    usage = st.session_state.get("ai_board_last_usage")
    if usage:
        with st.expander("Last AI turn", expanded=False):
            st.write(
                "Input tokens:",
                usage.get("input_tokens") if usage.get("input_tokens") is not None else "—",
            )
            st.write(
                "Output tokens:",
                usage.get("output_tokens") if usage.get("output_tokens") is not None else "—",
            )
            calls = usage.get("tool_calls") or []
            st.write("Planner tools:", ", ".join(calls) if calls else "None")
