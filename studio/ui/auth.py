from __future__ import annotations

import hmac
import streamlit as st

SESSION_KEY = "studio_unlocked"


def _get_expected_pin() -> str:
    """
    Read the Studio PIN from Streamlit Secrets.

    Configure it in:
    Streamlit Cloud -> Manage app -> Settings -> Secrets

    Example:
        STUDIO_PIN = "your-private-pin"

    Never commit the real PIN to GitHub.
    """
    try:
        return str(st.secrets.get("STUDIO_PIN", "")).strip()
    except Exception:
        return ""


def is_studio_unlocked() -> bool:
    """Return whether Studio Mode is unlocked for the current browser session."""
    return bool(st.session_state.get(SESSION_KEY, False))


def require_studio_pin() -> bool:
    """
    Require Studio PIN access.

    Fail-closed behavior:
    - If STUDIO_PIN is missing, Studio stays locked.
    - If the PIN is wrong, Studio stays locked.
    - A correct PIN unlocks Studio only for the current Streamlit session.
    """
    if is_studio_unlocked():
        return True

    expected_pin = _get_expected_pin()

    st.markdown("## 🔒 Studio Mode")
    st.caption(
        "Studio Mode contains developer tools, provider settings, "
        "production diagnostics and internal project data."
    )

    if not expected_pin:
        st.error(
            "Studio PIN is not configured. "
            "Add STUDIO_PIN in Streamlit Cloud → App settings → Secrets."
        )
        return False

    with st.form("studio_unlock_form", clear_on_submit=True):
        entered_pin = st.text_input(
            "Studio PIN",
            type="password",
            placeholder="Enter Studio PIN",
            autocomplete="off",
        )
        submitted = st.form_submit_button(
            "🔓 Unlock Studio",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if hmac.compare_digest(entered_pin.strip(), expected_pin):
            st.session_state[SESSION_KEY] = True
            st.rerun()
        else:
            st.error("Incorrect PIN.")

    return False


def lock_studio() -> None:
    """Lock Studio Mode for the current browser session."""
    st.session_state[SESSION_KEY] = False
    st.rerun()
