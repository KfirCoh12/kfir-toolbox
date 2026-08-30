"""Optional authentication gate for private hosted deployments.

Local development remains open by default. A hosted deployment opts into the gate
with ``KFIR_TOOLBOX_REQUIRE_AUTH=1`` and configures Streamlit OIDC secrets outside
the repository. An optional comma-separated email allowlist provides an additional
application-level restriction after the identity provider has authenticated a user.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

_REQUIRE_AUTH_ENV = "KFIR_TOOLBOX_REQUIRE_AUTH"
_ALLOWED_EMAILS_ENV = "KFIR_TOOLBOX_ALLOWED_EMAILS"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def authentication_required(environment: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environment is None else environment
    return env.get(_REQUIRE_AUTH_ENV, "").strip().lower() in _TRUE_VALUES


def allowed_emails(environment: Mapping[str, str] | None = None) -> frozenset[str]:
    env = os.environ if environment is None else environment
    raw = env.get(_ALLOWED_EMAILS_ENV, "")
    return frozenset(item.strip().lower() for item in raw.split(",") if item.strip())


def _user_email(user) -> str | None:
    try:
        data = user.to_dict()
    except (AttributeError, TypeError):
        data = {}
    email = data.get("email") if isinstance(data, dict) else None
    if email is None:
        try:
            email = user.email
        except (AttributeError, KeyError):
            return None
    normalized = str(email).strip().lower()
    return normalized or None


def require_authenticated_user(st, environment: Mapping[str, str] | None = None) -> str | None:
    """Stop a Streamlit page unless private-deployment authentication succeeds.

    Returns the normalized authenticated email when available. When authentication
    is not enabled, returns ``None`` immediately and does not touch Streamlit's auth
    API, preserving compatibility with existing local installations.
    """
    if not authentication_required(environment):
        return None

    user = getattr(st, "user", None)
    login = getattr(st, "login", None)
    if user is None or login is None:
        st.error("Private deployment authentication requires a Streamlit version with OIDC support.")
        st.stop()
        return None

    try:
        logged_in = bool(user.is_logged_in)
    except (AttributeError, KeyError):
        logged_in = False

    if not logged_in:
        st.button("Log in", on_click=login, type="primary")
        st.stop()
        return None

    email = _user_email(user)
    permitted = allowed_emails(environment)
    if permitted and email not in permitted:
        st.error("This authenticated account is not authorized to use this private toolbox.")
        logout = getattr(st, "logout", None)
        if logout is not None:
            st.button("Log out", on_click=logout)
        st.stop()
        return None

    return email
