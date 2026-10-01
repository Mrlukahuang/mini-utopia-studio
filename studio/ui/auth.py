from __future__ import annotations

import hmac
import streamlit as st

SESSION_KEY = "studio_unlocked"


def _get_expected_pin() -> str:
    try:
        return str(st.secrets.get("STUDIO_PIN", "")).strip()
    except Exception:
        return ""


def is_studio_unlocked() -> bool:
    return bool(st.session_state.get(SESSION_KEY, False))


def require_studio_pin() -> bool:
    if is_studio_unlocked():
        return True

    expected_pin = _get_expected_pin()

    st.markdown("### 🔒 Studio Mode")
    st.caption("Studio Mode contains developer tools and production diagnostics.")

    if not expected_pin:
        st.warning(
            "Studio PIN is not configured yet. "
            "Add STUDIO_PIN to Streamlit Secrets before using Studio Mode."
        )
        return False

    with st.form("studio_unlock_form", clear_on_submit=True):
        entered_pin = st.text_input(
            "Enter Studio PIN",
            type="password",
            placeholder="Studio PIN",
        )
        submitted = st.form_submit_button(
            "🔓 Unlock Studio",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if hmac.compare_digest(entered_pin.strip(), expected_pin):
            st.session_state[SESSION_KEY] = True
            st.rerun()
        else:
            st.error("Incorrect PIN.")

    return False


def lock_studio() -> None:
    st.session_state[SESSION_KEY] = False
    st.rerun()
