from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from studio.core.config import get_settings
from studio.core.enums import AssetType, ReviewStatus, StoryMode
from studio.models.character import CharacterProfile, EyeProfile
from studio.models.world import WorldBlueprint, WorldProfile
from studio.recipes.character_factory import CharacterFactoryRecipe
from studio.runtime.three_world import build_world_runtime_html, runtime_summary
from studio.services.bootstrap import build_context
from studio.services.style_service import StyleService
from studio.ui.auth import (
    lock_creator,
    lock_studio,
    require_creator_pin,
    require_studio_pin,
)
from studio.ui.brand import render_primary_brand, render_sidebar_brand
from studio.ui.creator.character_factory import render_character_factory
from studio.ui.creator.world_factory import render_world_factory
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
render_sidebar_brand()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "char_draft" not in st.session_state:
    st.session_state.char_draft = None

# Cross-page navigation is queued by creator workflows and applied before the
# sidebar radio is instantiated. This avoids mutating a live widget key.
pending_page = st.session_state.pop("pending_app_page", None)
if pending_page:
    st.session_state.app_page = pending_page


def archive_character(asset_id: str) -> None:
    """Soft-delete a Character while preserving references for Stories/Worlds."""
    ctx.assets.archive_character(asset_id)
    st.session_state.pop(f"confirm_delete_{asset_id}", None)


def explore_world(asset_id: str) -> None:
    """Open an approved Blueprint in the browser 3D runtime."""
    st.session_state.selected_world_id = asset_id
    st.session_state.app_page = "🎮 Explore World"


def edit_world(asset) -> None:
    """Load an existing Mini World back into World Factory."""
    profile = WorldProfile.model_validate(
        asset.metadata.get("world_profile", {})
    )
    st.session_state.world_draft = profile
    st.session_state.world_source = asset.description or profile.source_description
    st.session_state.world_name = asset.display_name
    st.session_state.editing_world_id = asset.asset_id
    st.session_state.world_creation_mode = "custom"
    st.session_state.world_stage = 0
    st.session_state.world_concept_candidates = []
    st.session_state.app_page = "🌍 World Factory"


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
    st.session_state.char_creation_mode = "custom"
    st.session_state.char_stage = 0
    st.session_state.character_master_candidate_path = None
    st.session_state.character_master_character_id = None
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


render_primary_brand()
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
        "🗺️ My Worlds",
        "🌍 World Factory",
        "🎮 Explore World",
        "🌎 Mini Utopia",
        "🧪 Playground",
        "📖 Stories",
    ],
    key="app_page",
)


creator_protected_pages = {
    "🎭 My Characters",
    "✨ Character Factory",
    "🗺️ My Worlds",
    "🌍 World Factory",
    "🎮 Explore World",
}
if mode == "🧒 Creator" and page in creator_protected_pages:
    if not require_creator_pin():
        st.stop()

    st.sidebar.success("🌈 Creator unlocked")
    if st.sidebar.button("🔒 Lock Creator", use_container_width=True):
        lock_creator()


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

    chars = [
        asset
        for asset in ctx.repository.list_assets(AssetType.CHARACTER)
        if asset.status != ReviewStatus.ARCHIVED
    ]

    if not chars:
        st.info(
            "还没有角色。去 Character Factory 创造第一个 Traveler 吧！"
        )

    for asset in chars:
        profile = CharacterProfile.model_validate(
            asset.metadata.get("character_profile", {})
        )
        master_ref = ctx.character_masters.current_master(asset.asset_id)

        with st.container(border=True):
            art_col, info_col, action_col = st.columns([1.35, 2.25, 0.72])

            with art_col:
                if master_ref:
                    try:
                        st.image(
                            ctx.storage.get_bytes(master_ref.path),
                            caption="✨ Character Master",
                            use_container_width=True,
                        )
                    except Exception:
                        st.markdown(
                            '<div class="mu-character-master-placeholder">🎭<br>'
                            '<span>Master image unavailable</span></div>',
                            unsafe_allow_html=True,
                        )
                        st.caption("旧图片文件暂时无法读取；角色资料仍然安全。下次编辑并重新生成后会恢复预览。")
                else:
                    st.markdown(
                        '<div class="mu-character-master-placeholder">🧸<br>'
                        '<span>No approved Master yet</span></div>',
                        unsafe_allow_html=True,
                    )

            with info_col:
                st.markdown(f"### {asset.display_name}")
                type_role = " · ".join(
                    part
                    for part in [profile.character_type, profile.story_role]
                    if part
                )
                if type_role:
                    st.caption(type_role)

                fact_a, fact_b = st.columns(2)
                with fact_a:
                    st.write(f"**Age / 年龄** · {profile.age or '—'}")
                    height_text = (
                        f"{profile.height_cm:.0f} cm"
                        if profile.height_cm is not None
                        else (profile.height or "—")
                    )
                    st.write(f"**Height / 身高** · {height_text}")
                    st.write(f"**Eyes / 眼睛** · {profile.eyes.color or '—'}")
                with fact_b:
                    hair = profile.hair_style or profile.hair_or_fur or "—"
                    st.write(f"**Hair / Fur / 发型毛发** · {hair}")
                    st.write(
                        f"**Build / 体型** · "
                        f"{profile.body_build or profile.body_type or '—'}"
                    )
                    st.write(
                        f"**Movement / 动作** · {profile.movement_style or '—'}"
                    )

                if profile.personality_traits:
                    st.markdown(
                        "".join(
                            f'<span class="mu-pill">{item}</span>'
                            for item in profile.personality_traits
                        ),
                        unsafe_allow_html=True,
                    )

                if profile.favorite_color_hexes:
                    swatches = "".join(
                        f'<span class="mu-color-dot" style="background:{hex_value}" '
                        f'title="{hex_value}"></span>'
                        for hex_value in profile.favorite_color_hexes
                    )
                    st.markdown(
                        f'<div class="mu-card-fact"><strong>Favorite Colors / 喜爱颜色</strong>'
                        f'<div class="mu-color-row">{swatches}</div></div>',
                        unsafe_allow_html=True,
                    )

                if profile.distinctive_features:
                    st.write(
                        "**Distinctive / 标志特征** · "
                        + " · ".join(profile.distinctive_features)
                    )

                if asset.description:
                    st.caption(asset.description)

            with action_col:
                st.button(
                    "✏️ Edit",
                    key=f"edit_{asset.asset_id}",
                    on_click=edit_character,
                    args=(asset,),
                    use_container_width=True,
                )

                confirm_key = f"confirm_delete_{asset.asset_id}"
                if not st.session_state.get(confirm_key):
                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_{asset.asset_id}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning("确定删除？")
                    if st.button(
                        "✅ Confirm",
                        key=f"confirm_delete_button_{asset.asset_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        archive_character(asset.asset_id)
                        st.rerun()
                    if st.button(
                        "↩ Cancel",
                        key=f"cancel_delete_{asset.asset_id}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = False
                        st.rerun()

                st.caption(f"v{asset.version}")

            if mode == "🛠 Studio" and studio_unlocked:
                with st.expander("🎨 Character Master Prompt", expanded=False):
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
                            profile=profile,
                            style_profile=style_profile,
                        ),
                        language="text",
                    )

                runtime_meta = asset.metadata.get("runtime_3d", {}) or {}
                with st.expander("🧍 Character 3D Runtime Asset", expanded=False):
                    if runtime_meta.get("model_path"):
                        st.success(
                            "GLB attached · " + runtime_meta.get("model_path", "")
                        )
                    else:
                        st.caption("No GLB attached · procedural avatar fallback is active.")

                    uploaded_glb = st.file_uploader(
                        "Upload Character GLB / 上传角色 GLB",
                        type=["glb"],
                        key=f"runtime_glb_{asset.asset_id}",
                        help="Studio-only prototype flow. The file is saved to ObjectStorage.",
                    )
                    scale = st.number_input(
                        "Runtime Scale",
                        min_value=0.05,
                        max_value=10.0,
                        value=float(runtime_meta.get("scale", 1.0)),
                        step=0.05,
                        key=f"runtime_scale_{asset.asset_id}",
                    )
                    clips = runtime_meta.get("animation_clips", {}) or {}
                    clip_a, clip_b, clip_c = st.columns(3)
                    with clip_a:
                        idle_clip = st.text_input(
                            "Idle clip",
                            value=clips.get("idle", "Idle"),
                            key=f"runtime_idle_{asset.asset_id}",
                        )
                    with clip_b:
                        walk_clip = st.text_input(
                            "Walk clip",
                            value=clips.get("walk", "Walk"),
                            key=f"runtime_walk_{asset.asset_id}",
                        )
                    with clip_c:
                        run_clip = st.text_input(
                            "Run clip",
                            value=clips.get("run", "Run"),
                            key=f"runtime_run_{asset.asset_id}",
                        )

                    attach_col, detach_col = st.columns(2)
                    with attach_col:
                        if st.button(
                            "💾 Attach GLB",
                            key=f"attach_runtime_glb_{asset.asset_id}",
                            disabled=uploaded_glb is None,
                            use_container_width=True,
                        ):
                            try:
                                ctx.character_runtime.attach_glb(
                                    asset_id=asset.asset_id,
                                    payload=uploaded_glb.getvalue(),
                                    scale=scale,
                                    idle_clip=idle_clip,
                                    walk_clip=walk_clip,
                                    run_clip=run_clip,
                                )
                                st.success("Character GLB attached.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"GLB attach failed: {exc}")
                    with detach_col:
                        if st.button(
                            "↩ Use Procedural",
                            key=f"detach_runtime_glb_{asset.asset_id}",
                            disabled=not bool(runtime_meta.get("model_path")),
                            use_container_width=True,
                        ):
                            ctx.character_runtime.detach_glb(asset.asset_id)
                            st.rerun()

                    st.caption(
                        "Prototype storage reminder: Streamlit local ObjectStorage is not durable yet. "
                        "We will move these assets to persistent object storage before production use."
                    )


elif page == "✨ Character Factory":
    render_character_factory(
        ctx,
        character_factory,
        studio_mode=(mode == "🛠 Studio" and studio_unlocked),
    )



elif page == "🗺️ My Worlds":
    render_game_hero(
        "My Mini Worlds 🗺️",
        "这些是你已经想象并选定视觉方向的世界。下一步会把它们真正搭成可以走进去的地方。",
        kicker="WORLD LIBRARY",
    )

    worlds = [
        asset
        for asset in ctx.repository.list_assets(AssetType.LOCATION)
        if asset.status != ReviewStatus.ARCHIVED
        and "world_profile" in asset.metadata
    ]

    if not worlds:
        st.info("还没有 Mini World。去 World Factory 创造第一个世界吧！")

    for asset in worlds:
        profile = WorldProfile.model_validate(
            asset.metadata.get("world_profile", {})
        )
        concept = ctx.world_concepts.current_concept(asset.asset_id)

        with st.container(border=True):
            art_col, info_col, action_col = st.columns([1.45, 2.15, 0.7])

            with art_col:
                if concept:
                    try:
                        st.image(
                            ctx.storage.get_bytes(concept.path),
                            caption="✨ Approved World Concept",
                            use_container_width=True,
                        )
                    except Exception:
                        st.markdown(
                            '<div class="mu-character-master-placeholder">🌍<br>'
                            '<span>Concept image unavailable</span></div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<div class="mu-character-master-placeholder">🏝️<br>'
                        '<span>No approved concept yet</span></div>',
                        unsafe_allow_html=True,
                    )

            with info_col:
                st.markdown(f"### {asset.display_name}")
                if profile.world_type or profile.reality_mode:
                    st.caption(
                        " · ".join(
                            x for x in [profile.world_type, profile.reality_mode] if x
                        )
                    )

                left, right = st.columns(2)
                with left:
                    st.write(f"**Season / 季节** · {profile.season or '—'}")
                    st.write(f"**Weather / 天气** · {profile.weather or '—'}")
                    st.write(f"**Time / 时间** · {profile.time_of_day or '—'}")
                with right:
                    st.write(
                        "**Terrain / 地形** · "
                        + (", ".join(profile.terrain) if profile.terrain else "—")
                    )
                    st.write(
                        "**Mood / 氛围** · "
                        + (", ".join(profile.mood) if profile.mood else "—")
                    )
                    st.write(f"**Portal / 传送门** · {profile.portal_form or '—'}")

                if profile.landmark_ideas:
                    st.write(
                        "**Landmarks / 地标** · " + " · ".join(profile.landmark_ideas)
                    )

                if profile.theme_color_hexes:
                    swatches = "".join(
                        f'<span class="mu-color-dot" style="background:{hex_value}" '
                        f'title="{hex_value}"></span>'
                        for hex_value in profile.theme_color_hexes
                    )
                    st.markdown(
                        f'<div class="mu-card-fact"><strong>Theme Colors / 世界主题色</strong>'
                        f'<div class="mu-color-row">{swatches}</div></div>',
                        unsafe_allow_html=True,
                    )

                blueprint = asset.metadata.get("world_blueprint")
                if blueprint:
                    st.success("🧩 Blueprint seed ready · 50×50 expandable world")
                else:
                    st.caption("Concept stage · waiting for Blueprint")

            with action_col:
                blueprint = asset.metadata.get("world_blueprint")
                st.button(
                    "🎮 Explore",
                    key=f"explore_world_{asset.asset_id}",
                    on_click=explore_world,
                    args=(asset.asset_id,),
                    disabled=not bool(blueprint),
                    use_container_width=True,
                )
                st.button(
                    "✏️ Edit",
                    key=f"edit_world_{asset.asset_id}",
                    on_click=edit_world,
                    args=(asset,),
                    use_container_width=True,
                )
                st.caption(f"v{asset.version}")


elif page == "🎮 Explore World":
    render_game_hero(
        "Explore Mini World 🎮",
        "这是第一版可玩的 3D Runtime：Blueprint 决定世界结构，Three.js 负责把它画出来。",
        kicker="M4 · PLAYABLE RUNTIME v0.1",
    )

    playable_worlds = [
        asset
        for asset in ctx.repository.list_assets(AssetType.LOCATION)
        if asset.status != ReviewStatus.ARCHIVED
        and asset.metadata.get("world_blueprint")
        and "world_profile" in asset.metadata
    ]

    if not playable_worlds:
        st.info("还没有可探索的 World Blueprint。先在 World Factory 选择并保存一个 Concept。")
    else:
        selected_id = st.session_state.get("selected_world_id")
        selected_index = next(
            (
                index
                for index, asset in enumerate(playable_worlds)
                if asset.asset_id == selected_id
            ),
            0,
        )
        selected = st.selectbox(
            "World / 选择世界",
            playable_worlds,
            index=selected_index,
            format_func=lambda asset: asset.display_name,
        )
        st.session_state.selected_world_id = selected.asset_id

        profile = WorldProfile.model_validate(
            selected.metadata.get("world_profile", {})
        )
        blueprint = WorldBlueprint.model_validate(
            selected.metadata.get("world_blueprint", {})
        )

        playable_characters = [
            asset
            for asset in ctx.repository.list_assets(AssetType.CHARACTER)
            if asset.status == ReviewStatus.APPROVED
            and "character_profile" in asset.metadata
        ]
        selected_character = None
        character_profile = None
        character_runtime = ctx.character_runtime.resolve(None)
        if playable_characters:
            selected_character = st.selectbox(
                "Traveler / 选择进入世界的角色",
                playable_characters,
                format_func=lambda asset: asset.display_name,
                key="runtime_character_asset",
            )
            character_profile = CharacterProfile.model_validate(
                selected_character.metadata.get("character_profile", {})
            )
            character_runtime = ctx.character_runtime.resolve(selected_character)
        else:
            st.caption("还没有 Approved Character，Runtime 会使用 Mini Traveler placeholder。")

        summary = runtime_summary(
            profile=profile,
            blueprint=blueprint,
            character_profile=character_profile,
        )

        a, b, c3, d = st.columns(4)
        a.metric("Grid", summary["grid"])
        b.metric("Chunks", summary["chunks"])
        c3.metric("Landmarks", summary["landmarks"])
        d.metric("Director Shots", summary["camera_points"])

        st.caption(
            "Controls: WASD / Arrow Keys · Hold Shift to Run · 第三人称跟随相机 · "
            "右上角可启动 Director Tour。"
        )
        st.caption(
            f"Character Runtime · {character_runtime.mode.upper()} · "
            f"Idle / Walk / Run clips: "
            f"{character_runtime.animation_clips.idle} / "
            f"{character_runtime.animation_clips.walk} / "
            f"{character_runtime.animation_clips.run}"
        )

        components.html(
            build_world_runtime_html(
                world_name=selected.display_name,
                profile=profile,
                blueprint=blueprint,
                character_name=(
                    selected_character.display_name
                    if selected_character is not None
                    else "Mini Traveler"
                ),
                character_profile=character_profile,
                character_runtime=character_runtime,
            ),
            height=760,
            scrolling=False,
        )

        with st.expander("🧩 Runtime Blueprint Inspector", expanded=False):
            st.json(blueprint.model_dump(mode="json"))


elif page == "🌍 World Factory":
    render_world_factory(
        ctx,
        style_asset_id=universe.style_asset_id,
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

    with st.expander("Storage", expanded=False):
        storage_backend = ctx.settings.object_storage_backend
        if storage_backend == "supabase":
            st.success("☁️ Durable Object Storage · Supabase")
            st.write(f"**Bucket** · {ctx.settings.supabase_storage_bucket}")
            st.caption(
                "Character Masters, World Concepts and Character GLBs are stored remotely. "
                "Service-role credentials remain server-side and are never sent to the browser."
            )
        else:
            st.warning("💻 Local Object Storage · development / ephemeral")
            st.caption(
                "Binary assets are stored on the local filesystem. On Streamlit Community Cloud "
                "they may disappear across redeploys or restarts."
            )

        st.write(
            "**Metadata database** · SQLite (still local / ephemeral on Streamlit Community Cloud)"
        )
        st.caption(
            "Next persistence milestone: move Studio metadata to durable Postgres so object keys "
            "and asset records survive together."
        )

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
