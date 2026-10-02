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
from studio.ui.theme import apply_mini_utopia_theme, render_brandbar, render_game_hero, render_quest


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

apply_mini_utopia_theme()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "char_draft" not in st.session_state:
    st.session_state.char_draft = None


def edit_character(asset) -> None:
    """Load an existing Character Asset back into the Creator flow."""
    profile = CharacterProfile.model_validate(
        asset.metadata.get("character_profile", {})
    )
    st.session_state.char_draft = profile
    st.session_state.char_source = asset.description or profile.source_description
    st.session_state.char_name = asset.display_name
    st.session_state.character_name_input = asset.display_name
    st.session_state.editing_character_id = asset.asset_id
    st.session_state.char_preview_ready = False
    st.session_state.app_page = "✨ Character Factory"


# ---------------------------------------------------------------------------
# App title
# ---------------------------------------------------------------------------

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


render_brandbar(studio=(mode == "🛠 Studio"))


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
    render_game_hero(
        "Charlotte & Chelsea’s Mini Utopia ✨",
        "Create a tiny hero, give them a world, and send them through a Portal. "
        "今天创造角色，明天一起去新的世界。",
        kicker="WELCOME BACK, CREATOR",
    )
    render_quest("今日任务 / Today’s Quest：创造一个让你一看到就想带去冒险的小伙伴。")

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
    st.subheader("Choose Your Adventure / 今天想创造什么？")

    a, b, c = st.columns(3)

    with a:
        st.markdown(
            '<div class="mu-world-card"><div class="emoji">🧸✨</div>'
            '<h3>Create a Character</h3><p>捏一个属于你的 Mini Playable Avatar。</p></div>',
            unsafe_allow_html=True,
        )

    with b:
        st.markdown(
            '<div class="mu-world-card"><div class="emoji">🏝️🌈</div>'
            '<h3>Build a Mini World</h3><p>创造漂浮岛、城堡、月球或任何世界。</p></div>',
            unsafe_allow_html=True,
        )

    with c:
        st.markdown(
            '<div class="mu-world-card"><div class="emoji">🪄🧪</div>'
            '<h3>Playground</h3><p>没有规则，先把疯狂想法放出来。</p></div>',
            unsafe_allow_html=True,
        )


elif page == "🎭 My Characters":
    render_game_hero(
        "My Little Heroes 🎭",
        "这些都是你创造过的伙伴。随时回来换衣服、改设定，再带 TA 去新的世界。",
        kicker="CHARACTER LIBRARY",
    )

    chars = ctx.repository.list_assets(AssetType.CHARACTER)

    if not chars:
        st.info(
            "还没有角色。去 Character Factory 创造第一个 Traveler 吧！"
        )

    for asset in chars:
        with st.container(border=True):
            st.markdown(
                '<div class="mu-character-card"><div class="mu-character-orb">🧸</div></div>',
                unsafe_allow_html=True,
            )
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

            st.button(
                "✏️ Edit Character / 编辑角色",
                key=f"edit_{asset.asset_id}",
                on_click=edit_character,
                args=(asset,),
                use_container_width=True,
            )

            if mode == "🛠 Studio" and studio_unlocked:
                with st.expander("🎨 Character Master Prompt", expanded=False):
                    profile_obj = CharacterProfile.model_validate(
                        asset.metadata.get("character_profile", {})
                    )
                    style_asset = (
                        ctx.repository.get_asset(universe.style_asset_id)
                        if universe.style_asset_id
                        else None
                    )
                    style_profile = (
                        style_asset.metadata.get("style_profile", {})
                        if style_asset
                        else {}
                    )
                    st.code(
                        ctx.character_master_prompts.compose(
                            name=asset.display_name,
                            profile=profile_obj,
                            style_profile=style_profile,
                        ),
                        language="text",
                    )


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
