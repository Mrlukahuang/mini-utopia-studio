from __future__ import annotations

from pathlib import Path

import streamlit as st


BRAND_NAME = "Mini Utopia"
BRAND_TAGLINE = "Travel Around Every World"

ASSET_DIR = Path(__file__).parent / "assets"
SQUARE_LOGO_PATH = ASSET_DIR / "mini_utopia_logo_badge.webp"
HORIZONTAL_LOGO_PATH = ASSET_DIR / "mini_utopia_logo_horizontal.webp"


def render_sidebar_brand() -> None:
    """Render the approved square Brand Canon asset in the sidebar."""
    st.sidebar.markdown('<div class="mu-sidebar-logo-shell">', unsafe_allow_html=True)
    st.sidebar.image(
        str(SQUARE_LOGO_PATH),
        use_container_width=True,
    )
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="mu-sidebar-tagline">Travel Around Every World</div>',
        unsafe_allow_html=True,
    )


def render_primary_brand() -> None:
    """Render the approved horizontal Brand Canon asset above page content."""
    st.markdown('<div class="mu-primary-logo-shell">', unsafe_allow_html=True)
    st.image(
        str(HORIZONTAL_LOGO_PATH),
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
