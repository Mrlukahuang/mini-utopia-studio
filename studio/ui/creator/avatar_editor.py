from __future__ import annotations

import streamlit as st

from studio.models.avatar import AvatarAppearance, BodyType
from studio.ui.creator.avatar_catalog import (
    AVATAR_COLOR_OPTIONS,
    BODY_TYPE_OPTIONS,
    EYE_STYLE_OPTIONS,
    HAIR_STYLE_OPTIONS,
    SPECIES_HEAD_OPTIONS,
    SURFACE_OPTIONS,
    allowed_eye_ids,
    allowed_hair_ids,
    allowed_surface_ids,
    option_ids,
    option_label,
    species_default_surface,
)
from studio.ui.creator.avatar_preview import render_avatar_preview


AVATAR_EDITOR_STATE_KEYS = (
    "avatar_body_type",
    "avatar_species_head",
    "avatar_surface_type",
    "avatar_surface_color",
    "avatar_eye_style",
    "avatar_eye_color",
    "avatar_hair_style",
    "avatar_hair_color",
)


def reset_avatar_editor_state() -> None:
    for key in AVATAR_EDITOR_STATE_KEYS:
        st.session_state.pop(key, None)


def _safe_index(values: list[str], current: str) -> int:
    try:
        return values.index(current)
    except ValueError:
        return 0


def _color_label(current_hex: str) -> str:
    normalized = (current_hex or "").lower()
    for label, value in AVATAR_COLOR_OPTIONS.items():
        if value.lower() == normalized:
            return label
    return next(iter(AVATAR_COLOR_OPTIONS))


def _filter_options(options, allowed: tuple[str, ...]):
    allowed_set = set(allowed)
    return tuple(option for option in options if option.option_id in allowed_set)


def render_avatar_appearance_editor(
    appearance: AvatarAppearance,
) -> AvatarAppearance:
    """Render the v1 modular Avatar controls and return the live selection."""

    st.markdown("#### 🧸 Playable Avatar / 可玩外观")
    st.caption(
        "身体和骨骼保持统一。你主要在换种族头、材质、眼睛、头发和颜色。"
    )

    left, preview_col = st.columns([1.2, 1], gap="large")

    with left:
        body_values = [item.value for item, _label in BODY_TYPE_OPTIONS]
        body_labels = {item.value: label for item, label in BODY_TYPE_OPTIONS}
        selected_body = st.selectbox(
            "Body Type / 体型",
            body_values,
            index=_safe_index(body_values, appearance.body_type.value),
            format_func=lambda value: body_labels[value],
            key="avatar_body_type",
        )

        species_ids = option_ids(SPECIES_HEAD_OPTIONS)
        selected_species = st.selectbox(
            "Species Head / 种族头型",
            species_ids,
            index=_safe_index(species_ids, appearance.species_head_id),
            format_func=lambda value: option_label(
                SPECIES_HEAD_OPTIONS, value
            ),
            key="avatar_species_head",
        )

        allowed_surfaces = allowed_surface_ids(selected_species)
        surface_options = _filter_options(SURFACE_OPTIONS, allowed_surfaces)
        surface_ids = option_ids(surface_options)
        current_surface = appearance.surface_type
        if current_surface not in surface_ids:
            current_surface = species_default_surface(selected_species)
        selected_surface = st.selectbox(
            "Surface / 皮肤 · 毛发 · 材质",
            surface_ids,
            index=_safe_index(surface_ids, current_surface),
            format_func=lambda value: option_label(surface_options, value),
            key="avatar_surface_type",
        )

        surface_color_label = st.selectbox(
            "Surface Color / 肤色 · 毛色 · 主体颜色",
            list(AVATAR_COLOR_OPTIONS),
            index=list(AVATAR_COLOR_OPTIONS).index(
                _color_label(appearance.surface_color_hex)
            ),
            key="avatar_surface_color",
        )

        allowed_eyes = allowed_eye_ids(selected_species)
        eye_options = _filter_options(EYE_STYLE_OPTIONS, allowed_eyes)
        eye_ids = option_ids(eye_options)
        current_eye = appearance.eye_style_id
        if current_eye not in eye_ids:
            current_eye = eye_ids[0]
        selected_eye = st.selectbox(
            "Eyes / 眼型",
            eye_ids,
            index=_safe_index(eye_ids, current_eye),
            format_func=lambda value: option_label(eye_options, value),
            key="avatar_eye_style",
        )
        eye_color_label = st.selectbox(
            "Eye Color / 眼睛颜色",
            list(AVATAR_COLOR_OPTIONS),
            index=list(AVATAR_COLOR_OPTIONS).index(
                _color_label(appearance.eye_color_hex)
            ),
            key="avatar_eye_color",
        )

        allowed_hair = allowed_hair_ids(selected_species)
        hair_options = _filter_options(HAIR_STYLE_OPTIONS, allowed_hair)
        hair_ids = option_ids(hair_options)
        current_hair = appearance.hair_style_id
        if current_hair not in hair_ids:
            current_hair = hair_ids[0]
        selected_hair = st.selectbox(
            "Hair Style / 发型",
            hair_ids,
            index=_safe_index(hair_ids, current_hair),
            format_func=lambda value: option_label(hair_options, value),
            key="avatar_hair_style",
        )
        hair_color_label = st.selectbox(
            "Hair Color / 发色",
            list(AVATAR_COLOR_OPTIONS),
            index=list(AVATAR_COLOR_OPTIONS).index(
                _color_label(appearance.hair_color_hex)
            ),
            disabled=selected_hair == "hair_none",
            key="avatar_hair_color",
        )

    result = appearance.model_copy(
        update={
            "customized": True,
            "body_type": BodyType(selected_body),
            "species_head_id": selected_species,
            "surface_type": selected_surface,
            "surface_color_hex": AVATAR_COLOR_OPTIONS[surface_color_label],
            "eye_style_id": selected_eye,
            "eye_color_hex": AVATAR_COLOR_OPTIONS[eye_color_label],
            "hair_style_id": selected_hair,
            "hair_color_hex": AVATAR_COLOR_OPTIONS[hair_color_label],
            "compatible_tags": ["humanoid", selected_species, selected_surface],
        }
    )

    with preview_col:
        render_avatar_preview(result)

    return result
