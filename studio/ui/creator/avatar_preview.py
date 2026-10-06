from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from studio.models.avatar import AvatarAppearance
from studio.runtime.avatar_preview_3d import build_avatar_preview_html
from studio.ui.creator.avatar_catalog import (
    EYE_STYLE_OPTIONS,
    HAIR_STYLE_OPTIONS,
    SPECIES_HEAD_OPTIONS,
    option_label,
)


def render_avatar_preview(
    appearance: AvatarAppearance,
    *,
    title: str = "Live 3D Avatar / 实时 3D 预览",
) -> None:
    """Render the reusable WebGL Avatar preview used by Creator/Dressing Room."""

    st.markdown(f"##### 🧸 {title}")
    st.caption(
        "真正 WebGL 3D · 与 Godot humanoid_kaykit_v1 共享体型比例和 Socket Contract。"
    )

    components.html(
        build_avatar_preview_html(appearance),
        height=620,
        scrolling=False,
    )

    species = option_label(SPECIES_HEAD_OPTIONS, appearance.species_head_id)
    eyes = option_label(EYE_STYLE_OPTIONS, appearance.eye_style_id)
    hair = option_label(HAIR_STYLE_OPTIONS, appearance.hair_style_id)

    tag_cols = st.columns(5)
    tag_cols[0].caption(f"🧬 {species}")
    tag_cols[1].caption(f"🧍 {appearance.body_type.value.title()}")
    tag_cols[2].caption(f"✨ {appearance.surface_type.title()}")
    tag_cols[3].caption(f"👁️ {eyes}")
    tag_cols[4].caption(f"💇 {hair}")
