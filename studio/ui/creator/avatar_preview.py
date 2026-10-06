from __future__ import annotations

from html import escape
from textwrap import dedent

import streamlit as st

from studio.models.avatar import AvatarAppearance, BodyType
from studio.ui.creator.avatar_catalog import (
    EYE_STYLE_OPTIONS,
    HAIR_STYLE_OPTIONS,
    SPECIES_HEAD_OPTIONS,
    option_label,
)


def render_avatar_preview(
    appearance: AvatarAppearance,
    *,
    title: str = "Live Avatar Preview / 实时预览",
) -> None:
    """Render a lightweight child-facing preview before the full 3D runtime.

    This is deliberately a fast visual feedback layer. The real Godot Avatar
    remains the runtime source of truth.
    """

    body_width = {
        BodyType.SLIM: 72,
        BodyType.STANDARD: 84,
        BodyType.CHUBBY: 98,
    }[appearance.body_type]

    species = option_label(SPECIES_HEAD_OPTIONS, appearance.species_head_id)
    eyes = option_label(EYE_STYLE_OPTIONS, appearance.eye_style_id)
    hair = option_label(HAIR_STYLE_OPTIONS, appearance.hair_style_id)

    head_radius = 34 if appearance.body_type != BodyType.CHUBBY else 38
    ear_html = ""
    if "sheep" in appearance.species_head_id:
        ear_html = '<span class="ear left">☁️</span><span class="ear right">☁️</span>'
    elif "cat" in appearance.species_head_id:
        ear_html = '<span class="ear left">▲</span><span class="ear right">▲</span>'
    elif "robot" in appearance.species_head_id:
        ear_html = '<span class="antenna">•</span>'
    elif "cloud" in appearance.species_head_id:
        ear_html = '<span class="cloudbits">☁️</span>'

    hair_html = ""
    if appearance.hair_style_id != "hair_none":
        hair_html = (
            f'<div class="hair" style="background:{escape(appearance.hair_color_hex)}"></div>'
        )

    st.markdown(
        dedent(
            f"""
        <div class="mu-avatar-preview">
          <div class="mu-avatar-title">{escape(title)}</div>
          <div class="avatar-stage">
            <div class="avatar" style="--body-w:{body_width}px;--head-r:{head_radius}px;">
              <div class="head" style="background:{escape(appearance.surface_color_hex)}">
                {ear_html}
                {hair_html}
                <div class="eyes">
                  <span style="background:{escape(appearance.eye_color_hex)}"></span>
                  <span style="background:{escape(appearance.eye_color_hex)}"></span>
                </div>
              </div>
              <div class="body" style="background:{escape(appearance.surface_color_hex)}"></div>
              <div class="legs">
                <span style="background:{escape(appearance.surface_color_hex)}"></span>
                <span style="background:{escape(appearance.surface_color_hex)}"></span>
              </div>
            </div>
          </div>
          <div class="avatar-tags">
            <span>{escape(species)}</span>
            <span>{escape(appearance.body_type.value.title())}</span>
            <span>{escape(appearance.surface_type.title())}</span>
            <span>{escape(eyes)}</span>
            <span>{escape(hair)}</span>
          </div>
        </div>
        <style>
          .mu-avatar-preview {{
            border:1px solid rgba(93,85,130,.14);
            border-radius:24px;
            padding:16px;
            background:linear-gradient(145deg,#fffaf0,#f3efff 55%,#ecfbff);
            box-shadow:0 10px 30px rgba(80,70,120,.08);
          }}
          .mu-avatar-title {{
            font-weight:800;
            margin-bottom:8px;
          }}
          .avatar-stage {{
            height:260px;
            display:flex;
            align-items:flex-end;
            justify-content:center;
            overflow:hidden;
            border-radius:18px;
            background:
              radial-gradient(circle at 50% 25%,rgba(255,255,255,.9),transparent 38%),
              linear-gradient(#dff4ff,#fff7e7);
          }}
          .avatar {{
            width:150px;
            height:220px;
            position:relative;
            display:flex;
            align-items:center;
            flex-direction:column;
            justify-content:flex-start;
            padding-top:8px;
          }}
          .head {{
            width:calc(var(--head-r) * 2);
            height:calc(var(--head-r) * 2);
            border-radius:44% 44% 48% 48%;
            position:relative;
            z-index:3;
            border:2px solid rgba(60,50,70,.08);
          }}
          .hair {{
            position:absolute;
            left:4px; right:4px; top:-3px;
            height:28px;
            border-radius:28px 28px 12px 12px;
            opacity:.96;
          }}
          .eyes {{
            position:absolute;
            top:34px; left:0; right:0;
            display:flex; justify-content:center; gap:17px;
          }}
          .eyes span {{
            width:10px; height:14px;
            border-radius:50%;
            box-shadow:inset 0 0 0 2px rgba(255,255,255,.65);
          }}
          .body {{
            width:var(--body-w);
            height:82px;
            margin-top:-6px;
            border-radius:28px 28px 22px 22px;
            border:2px solid rgba(60,50,70,.08);
            z-index:2;
          }}
          .legs {{
            display:flex; gap:12px;
            margin-top:-4px;
          }}
          .legs span {{
            width:22px; height:48px;
            border-radius:0 0 12px 12px;
            border:2px solid rgba(60,50,70,.07);
          }}
          .ear {{
            position:absolute; top:9px; font-size:25px; z-index:-1;
          }}
          .ear.left {{ left:-24px; transform:rotate(-18deg); }}
          .ear.right {{ right:-24px; transform:rotate(18deg); }}
          .antenna {{
            position:absolute; top:-29px; left:calc(50% - 6px);
            font-size:34px;
          }}
          .cloudbits {{
            position:absolute; top:-24px; left:-16px;
            font-size:45px; opacity:.85; z-index:-1;
          }}
          .avatar-tags {{
            display:flex; flex-wrap:wrap; gap:7px;
            margin-top:10px;
          }}
          .avatar-tags span {{
            background:rgba(255,255,255,.85);
            border:1px solid rgba(90,80,120,.12);
            border-radius:999px;
            padding:5px 9px;
            font-size:12px;
          }}
        </style>
            """
        ),
        unsafe_allow_html=True,
    )
