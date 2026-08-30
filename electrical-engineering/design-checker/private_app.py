"""Fail-closed entrypoint for the privately hosted toolbox."""
from __future__ import annotations

import streamlit as st

from src.auth import authentication_required, require_authenticated_user


if not authentication_required():
    st.set_page_config(page_title="Private Toolbox", page_icon="🔒", layout="centered")
    st.error(
        "Private hosting is not enabled. Set KFIR_TOOLBOX_REQUIRE_AUTH=1 and configure "
        "the OIDC secrets before exposing this entrypoint."
    )
    st.stop()

require_authenticated_user(st)

navigation = st.navigation(
    [
        st.Page("app.py", title="Electrical Design Checker", icon="⚡", default=True),
        st.Page("pages/3_Board_Planner.py", title="Board Planner", icon="⚡"),
    ]
)
navigation.run()
