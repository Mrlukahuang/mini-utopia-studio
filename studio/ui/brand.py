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
    """Render the approved horizontal Brand Canon asset above page content."""
    st.markdown(
        f"""
        <div class="mu-primary-logo-shell">
            <img class="mu-primary-logo" src="{_data_uri(HORIZONTAL_LOGO_PATH)}"
                 alt="Mini Utopia logo">
        </div>
        """,
        unsafe_allow_html=True,
    )
