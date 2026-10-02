from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


BRAND_NAME = "Mini Utopia"
BRAND_TAGLINE = "Travel Around Every World"

ASSET_DIR = Path(__file__).parent / "assets"
SQUARE_LOGO_PATH = ASSET_DIR / "mini_utopia_logo_badge.webp"
HORIZONTAL_LOGO_PATH = ASSET_DIR / "mini_utopia_logo_horizontal.webp"


def _data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


def render_sidebar_brand() -> None:
    """Render the approved square Brand Canon asset in the sidebar."""
    st.sidebar.markdown(
        f"""
        <div class="mu-sidebar-logo-shell">
            <img class="mu-sidebar-logo" src="{_data_uri(SQUARE_LOGO_PATH)}"
                 alt="Mini Utopia square logo">
        </div>
        <div class="mu-sidebar-tagline">{BRAND_TAGLINE}</div>
        """,
        unsafe_allow_html=True,
    )


def render_primary_brand() -> None:
    """Render the approved horizontal Brand Canon asset above page content.

    Use Streamlit's native image renderer here instead of embedding a large
    base64 data URI in HTML. Streamlit Cloud can sanitize or fail to render
    large data-URI images even when smaller sidebar images still work.
    """
    with st.container():
        st.markdown('<div class="mu-primary-logo-shell">', unsafe_allow_html=True)
        st.image(
            str(HORIZONTAL_LOGO_PATH),
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
