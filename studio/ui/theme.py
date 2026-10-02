from __future__ import annotations

import streamlit as st


MINI_UTOPIA_CSS = r"""
<style>
:root {
    --mu-ink: #2D3150;
    --mu-muted: #73758E;
    --mu-pink: #F7B7D2;
    --mu-mint: #B9E7D0;
    --mu-lavender: #D7C2F3;
    --mu-blue: #BDE3F7;
    --mu-peach: #F8CBAE;
    --mu-cream: #FFF4D7;
    --mu-white: rgba(255,255,255,.90);
}

html, body, [class*="css"] {
    color: var(--mu-ink);
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 8% 8%, rgba(255,255,255,.96) 0 7%, transparent 8%),
        radial-gradient(circle at 90% 18%, rgba(255,255,255,.74) 0 5%, transparent 6%),
        linear-gradient(180deg, #CDEBFF 0%, #E9E2FF 35%, #FFF0F5 70%, #FFF8E7 100%);
    background-attachment: fixed;
}

[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after {
    content: "";
    position: fixed;
    z-index: 0;
    pointer-events: none;
    filter: blur(.2px);
}

[data-testid="stAppViewContainer"]::before {
    width: 270px;
    height: 105px;
    left: 10%;
    top: 7%;
    border-radius: 60% 45% 55% 45%;
    background: rgba(255,255,255,.46);
    box-shadow:
        80px 22px 0 12px rgba(255,255,255,.34),
        150px -8px 0 -8px rgba(255,255,255,.30);
}

[data-testid="stAppViewContainer"]::after {
    width: 220px;
    height: 86px;
    right: 7%;
    bottom: 8%;
    border-radius: 55% 48% 52% 48%;
    background: rgba(255,255,255,.30);
    box-shadow:
        -75px 18px 0 8px rgba(255,255,255,.25);
}

.block-container {
    max-width: 1160px;
    padding-top: 3.25rem;
    padding-bottom: 5rem;
    position: relative;
    z-index: 1;
}

[data-testid="stHeader"] {
    background: rgba(205,235,255,.72);
    backdrop-filter: blur(10px);
}

[data-testid="stToolbar"] {
    top: .35rem;
}

@media (max-width: 768px) {
    .block-container {
        padding-top: 3.75rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(255,255,255,.92), rgba(249,244,255,.91));
    border-right: 1px solid rgba(104,98,160,.10);
    box-shadow: 12px 0 36px rgba(73,65,123,.06);
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    border-radius: 16px;
    padding: .28rem .5rem;
    transition: .15s ease;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(215,194,243,.22);
    transform: translateX(2px);
}

h1, h2, h3 {
    color: var(--mu-ink);
    letter-spacing: -.02em;
}

.stButton > button {
    border: 1px solid rgba(103,91,168,.12);
    border-radius: 18px;
    min-height: 3rem;
    padding: .55rem 1.05rem;
    font-weight: 760;
    color: #4C456E;
    background: linear-gradient(135deg, #FFFDF8, #F2EDFF);
    box-shadow: 0 8px 22px rgba(74,64,124,.08), inset 0 1px 0 rgba(255,255,255,.95);
    transition: transform .13s ease, box-shadow .13s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    border-color: rgba(122,102,207,.24);
    box-shadow: 0 12px 28px rgba(74,64,124,.13);
}

.stButton > button[kind="primary"] {
    color: #514375;
    border-color: rgba(238,157,190,.24);
    background: linear-gradient(135deg, #FFE1EC 0%, #F2E6FF 52%, #DDF5EC 100%);
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
    border-radius: 16px !important;
    border-color: rgba(111,102,165,.14) !important;
    background: rgba(255,255,255,.86) !important;
}

[data-testid="stExpander"],
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 24px !important;
}

[data-testid="stMetric"] {
    background: rgba(255,255,255,.82);
    border: 1px solid rgba(108,92,231,.10);
    padding: 15px;
    border-radius: 22px;
    box-shadow: 0 10px 26px rgba(38,32,72,.06);
}

.mu-brandbar {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:16px;
    padding:4px 4px 18px 4px;
    margin-top:.25rem;
}

.mu-brand {
    font-size:1.08rem;
    font-weight:850;
    color:#514A71;
}

.mu-brand-badge {
    display:inline-block;
    padding:6px 11px;
    border-radius:999px;
    font-size:.75rem;
    font-weight:800;
    background:rgba(255,255,255,.75);
    border:1px solid rgba(108,92,231,.10);
}

.mu-game-hero {
    position:relative;
    overflow:hidden;
    padding:38px 38px 34px;
    border-radius:34px;
    background:
        radial-gradient(circle at 87% 20%, rgba(255,255,255,.72) 0 8%, transparent 9%),
        linear-gradient(135deg, rgba(255,246,206,.94), rgba(242,224,255,.94) 45%, rgba(214,242,255,.95));
    border:1px solid rgba(114,100,180,.11);
    box-shadow:0 22px 54px rgba(80,68,134,.12), inset 0 1px 0 rgba(255,255,255,.9);
    margin-bottom:22px;
}

.mu-game-hero::after {
    content:"☁️   ✨   ⭐";
    position:absolute;
    right:24px;
    bottom:16px;
    font-size:1.55rem;
    opacity:.48;
    letter-spacing:.5rem;
}

.mu-game-hero h1 {
    margin:0;
    max-width:760px;
    font-size:clamp(2rem,5vw,3.35rem);
    line-height:1.02;
    color:#353251;
}

.mu-game-hero p {
    max-width:720px;
    margin:14px 0 0;
    color:#666580;
    font-size:1.03rem;
}

.mu-game-kicker {
    display:inline-flex;
    align-items:center;
    gap:7px;
    margin-bottom:10px;
    padding:6px 11px;
    border-radius:999px;
    color:#7162B1;
    background:rgba(255,255,255,.66);
    font-size:.78rem;
    font-weight:850;
    letter-spacing:.04em;
}

.mu-world-card {
    min-height:150px;
    padding:22px;
    border-radius:28px;
    background:rgba(255,255,255,.78);
    border:1px solid rgba(111,96,176,.10);
    box-shadow:0 12px 30px rgba(72,63,118,.07);
    margin-bottom:12px;
}

.mu-world-card .emoji {
    font-size:2rem;
    margin-bottom:8px;
}

.mu-world-card h3 {
    margin:0 0 6px;
}

.mu-world-card p {
    color:#72738A;
    margin:0;
}

.mu-character-card {
    padding:20px 20px 14px;
    border-radius:26px;
    background:
        linear-gradient(145deg, rgba(255,255,255,.92), rgba(247,240,255,.86));
    border:1px solid rgba(113,100,176,.10);
    box-shadow:0 10px 28px rgba(71,61,121,.07);
    margin-bottom:10px;
}

.mu-character-orb {
    width:54px;
    height:54px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius:19px;
    background:linear-gradient(135deg,#FFD9E7,#DCC9FA,#C9F1DE);
    font-size:1.7rem;
    box-shadow:inset 0 1px 0 #fff;
}

.mu-note {
    padding:16px 18px;
    border-radius:19px;
    background:rgba(235,248,255,.78);
    border:1px solid rgba(43,143,216,.10);
    color:#3B5266;
}

.mu-pill {
    display:inline-block;
    padding:5px 10px;
    margin-right:6px;
    margin-bottom:6px;
    border-radius:999px;
    background:rgba(215,194,243,.25);
    color:#62579A;
    font-size:.82rem;
    font-weight:700;
}

.mu-quest {
    padding:12px 16px;
    border-radius:18px;
    background:linear-gradient(90deg, rgba(255,236,196,.75), rgba(248,220,238,.72), rgba(220,239,255,.72));
    border:1px solid rgba(108,92,231,.08);
    color:#59546F;
    font-weight:700;
    margin:8px 0 18px;
}

.mu-step-card {
    border-radius:26px !important;
    padding:19px 21px 9px !important;
    margin:13px 0 18px !important;
    background:linear-gradient(135deg, rgba(255,248,221,.84), rgba(245,232,255,.80), rgba(230,247,255,.84)) !important;
    border:1px solid rgba(113,103,180,.10) !important;
    box-shadow:0 10px 26px rgba(73,64,121,.055);
}

.mu-step-kicker {
    font-size:.79rem !important;
    font-weight:850 !important;
    letter-spacing:.05em !important;
    color:#7869B8 !important;
}

.mu-review {
    border-radius:26px;
    padding:20px 22px;
    background:linear-gradient(135deg,rgba(255,232,239,.80),rgba(237,245,255,.88));
    border:1px solid rgba(244,143,177,.20);
}

hr {
    border-color:rgba(93,81,145,.08) !important;
}
</style>
"""


def apply_mini_utopia_theme() -> None:
    st.markdown(MINI_UTOPIA_CSS, unsafe_allow_html=True)


def render_brandbar(*, studio: bool = False) -> None:
    badge = "🛠 Studio Mode" if studio else "🎮 Creator Mode"
    st.markdown(
        f"""
        <div class="mu-brandbar">
            <div class="mu-brand">✨ Mini Utopia <span style="opacity:.55">· Travel Around Every World</span></div>
            <div class="mu-brand-badge">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_game_hero(
    title: str,
    subtitle: str,
    *,
    kicker: str = "SMALL WORLDS · BIG IMAGINATION",
) -> None:
    st.markdown(
        f"""
        <section class="mu-game-hero">
            <div class="mu-game-kicker">✨ {kicker}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_quest(text: str) -> None:
    st.markdown(f'<div class="mu-quest">⭐ {text}</div>', unsafe_allow_html=True)
