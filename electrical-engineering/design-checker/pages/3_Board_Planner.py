"""Production Board Planner HMI workspace."""
import streamlit as st

from src.board_planner_hmi import render_board_planner
from src.working_board_baseline import ensure_office_working_baseline

st.set_page_config(
    page_title="Board Planner",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# During development, retain the realistic office fixture as the shared baseline only
# when there is no board or the exact legacy two-circuit demo is still persisted.
ensure_office_working_baseline()
render_board_planner()
