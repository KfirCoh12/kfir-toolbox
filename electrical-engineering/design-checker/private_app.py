"""Fail-closed entrypoint for the privately hosted toolbox."""
from __future__ import annotations

import streamlit as st

from src.auth import allowed_emails, authentication_required, require_authenticated_user
from src.board_persistence import persistence_scope_for_email


if not authentication_required():
    st.set_page_config(page_title="Private Toolbox", page_icon="🔒", layout="centered")
    st.error(
        "Private hosting is not enabled. Set KFIR_TOOLBOX_REQUIRE_AUTH=1 and configure "
        "the OIDC secrets before exposing this entrypoint."
    )
    st.stop()

if not allowed_emails():
    st.set_page_config(page_title="Private Toolbox", page_icon="🔒", layout="centered")
    st.error(
        "Private hosting is locked because no authorized account is configured. "
        "Set KFIR_TOOLBOX_ALLOWED_EMAILS to one or more explicitly permitted email addresses."
    )
    st.stop()

email = require_authenticated_user(st)
if email is None:
    st.error("Private hosting could not establish an authenticated user identity.")
    st.stop()

navigation = st.navigation(
    [
        st.Page("app.py", title="Electrical Design Checker", icon="⚡", default=True),
        st.Page("pages/3_Board_Planner.py", title="Board Planner", icon="⚡"),
    ]
)
with persistence_scope_for_email(email):
    navigation.run()
