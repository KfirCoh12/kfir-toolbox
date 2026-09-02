"""Experimental Board Planner UI/UX sandbox."""
import streamlit as st

from src.board_persistence import save_last_board
from src.hmi_planner_workspace import render_workspace
from src.sample_boards import office_700m2_150_people_board

st.set_page_config(
    page_title="Board Planner · HMI Preview",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

with st.popover("Load test board", use_container_width=False):
    st.markdown("**Office stress fixture**")
    st.caption("700 m² · ~150 people · declared 400 A feed · 40 final circuits across 5 distribution fields.")
    st.caption("This replaces the current working-board autosave so Board Planner and Protection Checks can use the same test case.")
    if st.button("Load office stress board", type="primary", use_container_width=True):
        save_last_board(office_700m2_150_people_board())
        for key in tuple(st.session_state.keys()):
            if key.startswith("tree_") or key.startswith("hmi_") or key.startswith("_hmi_") or key == "_tree_persistence_loaded":
                st.session_state.pop(key, None)
        st.success("Office stress board loaded.")
        st.rerun()

render_workspace()
