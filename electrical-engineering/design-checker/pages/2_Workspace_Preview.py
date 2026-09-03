"""Experimental Board Planner UI/UX sandbox."""
import streamlit as st

from src.hmi_planner_workspace import render_workspace
from src.working_board_baseline import ensure_office_working_baseline

st.set_page_config(
    page_title="Board Planner · HMI Preview",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ensure_office_working_baseline()
render_workspace()
