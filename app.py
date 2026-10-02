from pathlib import Path

import streamlit as st

from studio.core.config import get_settings
from studio.core.enums import AssetType, StoryMode
from studio.models.character import CharacterProfile, EyeProfile
from studio.recipes.character_factory import CharacterFactoryRecipe
from studio.services.bootstrap import build_context
from studio.services.style_service import StyleService
from studio.ui.auth import lock_studio, require_studio_pin
from studio.ui.creator.character_factory import render_character_factory


ROOT = Path(__file__).parent

st.set_page_config(
    page_title="Mini Utopia Studio",
    page_icon="✨",
    layout="wide",
)

ctx = build_context(get_settings(ROOT))
universe = ctx.universes.ensure_mini_utopia()
# Construct the style service from the repository at the app boundary.
# This stays safe during Streamlit hot-reload when an older StudioContext
# object may briefly remain in memory while app.py has already refreshed.
style_service = StyleService(ctx.repository)
universe = style_service.attach_base_style(universe)
character_factory = CharacterFactoryRecipe(ctx.registry, ctx.assets)


# ---------------------------------------------------------------------------
# Visual layer
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .stButton > button {
        border-radius: 16px;
        min-height: 2.8rem;
        font-weight: 650;
    }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,.94);
        border: 1px solid rgba(108,92,231,.14);
        padding: 16px;
        border-radius: 20px;
        box-shadow: 0 8px 30px rgba(38,32,72,.06);
    }

    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #20243a !important;
    }

    .mu-hero {
        padding: 28px 30px;
        border-radius: 28px;
        background: linear-gradient(
            135deg,
            rgba(255,244,208,.96),
            rgba(236,245,255,.96)
        );
        border: 1px solid rgba(108,92,231,.10);
        margin-bottom: 22px;
    }

    .mu-hero h1 {
        color: #25233b;
        margin: 0 0 8px 0;
        font-size: 2.35rem;
        line-height: 1.12;
    }

    .mu-hero p {
        color: #55546b;
        font-size: 1.05rem;
        margin: 0;
    }

    .mu-note {
        padding: 16px 18px;
        border-radius: 18px;
        background: rgba(226,245,255,.72);
        border: 1px solid rgba(43,143,216,.12);
        color: #23415c;
    }

    .mu-pill {
        display: inline-block;
        padding: 5px 10px;
        margin-right: 6px;
        margin-bottom: 6px;
        border-radius: 999px;
        background: rgba(108,92,231,.10);
        color: #5b50be;
        font-size: .85rem;
        font-weight: 600;
    }

    div[data-testid="stSidebar"] {
        border-right: 1px solid rgba(125,125,145,.12);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "char_draft" not in st.session_state:
    st.session_state.char_draft = None


# ---------------------------------------------------------------------------
# App title
# ---------------------------------------------------------------------------

st.title("❤️✨ Charlotte & Chelsea ✨❤️ 的 Utopia (乌托邦) ✨☁️")


# ---------------------------------------------------------------------------
# Mode selection — IMPORTANT:
# Studio authentication happens BEFORE Studio pages are rendered.
# ---------------------------------------------------------------------------

mode = st.sidebar.radio(
    "Mode",
    ["🧒 Creator", "🛠 Studio"],
    key="app_mode",
)

studio_unlocked = False

if mode == "🛠 Studio":
    st.sidebar.divider()

    studio_unlocked = require_studio_pin()

    if not studio_unlocked:
        st.sidebar.caption("🔒 Studio is locked.")
        st.stop()

    st.sidebar.success("🔓 Studio unlocked")
    st.sidebar.caption("Foundation v0.3")
    st.sidebar.caption(
        "Capabilities: " + ", ".join(ctx.registry.list_capabilities())
    )

    if st.sidebar.button(
        "🔒 Lock Studio",
        use_container_width=True,
    ):
        lock_studio()


# ---------------------------------------------------------------------------
# Page navigation
# Only appears after Studio is authenticated, or immediately in Creator Mode.
# ---------------------------------------------------------------------------

page = st.sidebar.radio(
    "Create",
    [
        "🏠 Home",
        "🎭 My Characters",
        "✨ Character Factory",
        "🌎 Mini Utopia",
        "🧪 Playground",
        "📖 Stories",
    ],
    key="app_page",
)


# ---------------------------------------------------------------------------
# Creator / shared pages
# ---------------------------------------------------------------------------

if page == "🏠 Home":
    st.markdown(
        """<div class="mu-hero">
<h1>Small Worlds. Big Imagination. ✨</h1>
<p>Create a character once, keep it forever, and take it anywhere. Today Auckland. Tomorrow the Moon. Next week — who knows?</p>
</div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "🎭 Characters",
        len(ctx.repository.list_assets(AssetType.CHARACTER)),
    )
    c2.metric(
        "🌍 Places",
        len(ctx.repository.list_assets(AssetType.LOCATION)),
    )
    c3.metric(
        "🎒 Objects",
        len(ctx.repository.list_assets(AssetType.PROP)),
    )
    c4.metric(
        "📖 Stories",
        len(ctx.repository.list_stories()),
    )

    st.markdown(
        """
        <div class="mu-note">
            <b>Creative LEGO:</b>
            角色、地点、道具和风格都是独立资产。
            Story 只负责把它们自由组合。
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.subheader("Where should we create today?")

    a, b, c = st.columns(3)

    with a:
        st.markdown("### 🎭 Character")
        st.caption("创造一个可以反复使用的角色。")

    with b:
        st.markdown("### 🌍 Mini World")
        st.caption("创造一个新的地点、星球或奇怪世界。")

    with c:
        st.markdown("### 🧪 Playground")
        st.caption("No rules. No canon. Just create.")


elif page == "🎭 My Characters":
    st.header("🎭 My Characters")

    chars = ctx.repository.list_assets(AssetType.CHARACTER)

    if not chars:
        st.info(
            "还没有角色。去 Character Factory 创造第一个 Traveler 吧！"
        )

    for asset in chars:
        with st.container(border=True):
            st.subheader(asset.display_name)
            st.caption(asset.asset_id)
            st.write(asset.description or "等待描述")

            profile = asset.metadata.get("character_profile", {})
            personality = profile.get("personality_traits", [])

            if personality:
                st.markdown(
                    "".join(
                        f'<span class="mu-pill">{item}</span>'
                        for item in personality
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("等待性格设定")


elif page == "✨ Character Factory":
    render_character_factory(
        ctx,
        character_factory,
        studio_mode=(mode == "🛠 Studio" and studio_unlocked),
    )


elif page == "🌎 Mini Utopia":
    st.header("🌎 Mini Utopia")
    st.subheader(universe.tagline)
    st.write(universe.description)

    st.markdown(
        "**Story Formula** · "
        + " → ".join(universe.story_formula)
    )

    st.markdown(
        "**Portal Rule** · "
        + universe.portal_rule
    )

    st.markdown("**Canon Rules**")

    for rule in universe.canon_rules:
        st.write("✓ " + rule)

    if universe.traveler_asset_id:
        traveler = ctx.repository.get_asset(
            universe.traveler_asset_id
        )

        st.success(
            "Current Traveler: "
            + (
                traveler.display_name
                if traveler
                else universe.traveler_asset_id
            )
        )
    else:
        st.caption(
            "Traveler 尚未锁定。确认第一个 Character Master 后"
            "再设为 Mini Utopia Traveler。"
        )


elif page == "🧪 Playground":
    st.header("🧪 Playground")
    st.write(
        "No rules. No canon. Just create. "
        "这里的实验不会自动改变 Mini Utopia。"
    )

    title = st.text_input("给这个疯狂想法一个名字")

    premise = st.text_area(
        "发生什么？",
        placeholder="例如：写实恐龙和水彩香蕉在学校打篮球……",
    )

    chars = ctx.repository.list_assets(AssetType.CHARACTER)

    selected = st.multiselect(
        "想带上哪些已有角色？",
        chars,
        format_func=lambda asset: asset.display_name,
    )

    if st.button(
        "Save Playground Story",
        disabled=not title or not premise,
    ):
        story = ctx.stories.create_story(
            title=title,
            premise=premise,
            mode=StoryMode.PLAYGROUND,
            asset_ids=[
                asset.asset_id
                for asset in selected
            ],
        )

        st.success(
            f"已保存：{story.story_id}"
        )


elif page == "📖 Stories":
    st.header("📖 Stories")

    stories = ctx.repository.list_stories()

    if not stories:
        st.info(
            "还没有 Story。可以先在 Playground 保存一个疯狂想法。"
        )

    for story in stories:
        with st.container(border=True):
            st.subheader(story.title)
            st.caption(
                f"{story.story_id} · {story.mode.value}"
            )
            st.write(story.premise)
            st.caption(
                "Assets: "
                + (
                    ", ".join(story.asset_ids)
                    or "none"
                )
            )


# ---------------------------------------------------------------------------
# Studio-only inspector
# This block is unreachable unless Studio authentication succeeded above.
# ---------------------------------------------------------------------------

if mode == "🛠 Studio" and studio_unlocked:
    st.divider()
    st.subheader("🛠 Studio Inspector")

    with st.expander(
        "Universe",
        expanded=False,
    ):
        st.json(
            universe.model_dump(mode="json")
        )

    with st.expander(
        "Assets",
        expanded=False,
    ):
        st.json(
            [
                asset.model_dump(mode="json")
                for asset in ctx.repository.list_assets()
            ]
        )

    with st.expander(
        "Jobs",
        expanded=False,
    ):
        st.json(
            [
                job.model_dump(mode="json")
                for job in ctx.repository.list_jobs()
            ]
        )
