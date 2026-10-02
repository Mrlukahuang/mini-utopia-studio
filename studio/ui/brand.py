from __future__ import annotations

import streamlit as st


BRAND_NAME = "Mini Utopia"
BRAND_TAGLINE = "Travel Around Every World"

SQUARE_LOGO_SVG = r"""
<div class="mu-sidebar-logo-shell" aria-label="Mini Utopia">
<svg class="mu-sidebar-logo" viewBox="0 0 320 320" role="img" aria-label="Mini Utopia logo">
  <defs>
    <linearGradient id="muBadgeBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#FFF7E8"/>
      <stop offset="50%" stop-color="#FFF0F6"/>
      <stop offset="100%" stop-color="#EAF7FF"/>
    </linearGradient>
    <linearGradient id="muWord" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F58FB3"/>
      <stop offset="52%" stop-color="#E99BCB"/>
      <stop offset="100%" stop-color="#9BCBF4"/>
    </linearGradient>
    <filter id="muShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#8C79B5" flood-opacity=".14"/>
    </filter>
  </defs>
  <rect x="20" y="20" width="280" height="280" rx="72" fill="url(#muBadgeBg)" stroke="#FFFFFF" stroke-width="8" filter="url(#muShadow)"/>
  <g transform="translate(160 79)">
    <path d="M0,-29 L8,-9 L30,-8 L13,5 L19,27 L0,15 L-19,27 L-13,5 L-30,-8 L-8,-9 Z" fill="#FFD45F"/>
    <circle cx="0" cy="0" r="7" fill="#FFF4C4"/>
  </g>
  <text x="160" y="151" text-anchor="middle" class="mu-logo-word">MINI</text>
  <text x="160" y="211" text-anchor="middle" class="mu-logo-word">UTOPIA</text>
  <g transform="translate(72 246)">
    <rect x="0" y="0" width="176" height="34" rx="17" fill="#FFFFFF" fill-opacity=".76"/>
    <text x="88" y="23" text-anchor="middle" class="mu-logo-small">PLAY · CREATE · EXPLORE</text>
  </g>
</svg>
</div>
"""

HORIZONTAL_LOGO_SVG = r"""
<div class="mu-primary-logo-shell" aria-label="Mini Utopia">
<svg class="mu-primary-logo" viewBox="0 0 980 220" role="img" aria-label="Mini Utopia logo">
  <defs>
    <linearGradient id="muWordWide" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F58FB3"/>
      <stop offset="50%" stop-color="#E79BD4"/>
      <stop offset="100%" stop-color="#90C8F6"/>
    </linearGradient>
    <linearGradient id="muMarkWide" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#FFF2C7"/>
      <stop offset="100%" stop-color="#F6D4F0"/>
    </linearGradient>
  </defs>
  <g transform="translate(18 20)">
    <rect x="0" y="0" width="180" height="180" rx="54" fill="url(#muMarkWide)" stroke="#FFFFFF" stroke-width="6"/>
    <path d="M90,36 L100,62 L128,63 L106,80 L113,108 L90,92 L67,108 L74,80 L52,63 L80,62 Z" fill="#FFD45F"/>
    <path d="M49,129 C69,112 111,112 131,129 C114,142 68,142 49,129 Z" fill="#B9E7D0"/>
    <circle cx="61" cy="126" r="8" fill="#F7B7D2"/>
    <circle cx="119" cy="126" r="8" fill="#D7C2F3"/>
  </g>
  <text x="232" y="102" class="mu-logo-word-wide">Mini Utopia</text>
  <text x="236" y="150" class="mu-logo-tagline">Travel Around Every World</text>
  <g transform="translate(810 64)">
    <circle cx="42" cy="42" r="42" fill="#FFFFFF" fill-opacity=".58"/>
    <path d="M42,11 L50,32 L72,33 L55,47 L61,68 L42,56 L23,68 L29,47 L12,33 L34,32 Z" fill="#F7B7D2"/>
  </g>
</svg>
</div>
"""


def render_sidebar_brand() -> None:
    st.sidebar.markdown(SQUARE_LOGO_SVG, unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="mu-sidebar-tagline">Travel Around Every World</div>',
        unsafe_allow_html=True,
    )


def render_primary_brand() -> None:
    st.markdown(HORIZONTAL_LOGO_SVG, unsafe_allow_html=True)
