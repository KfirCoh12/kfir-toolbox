"""Experimental Board Planner UI/UX sandbox."""
import streamlit as st

from src.hmi_planner_workspace import render_workspace

st.set_page_config(
    page_title="Board Planner · HMI Preview",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_workspace()
