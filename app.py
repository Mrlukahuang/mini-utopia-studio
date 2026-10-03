from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from studio.core.config import get_settings
from studio.core.enums import AssetType, ReviewStatus, StoryMode
from studio.models.character import CharacterProfile, EyeProfile
from studio.models.render import WorldRenderSpec
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
from studio.ui.creator.character_factory import render_character_factory, reset_character_creation_state
from studio.ui.creator.world_factory import render_world_factory
from studio.ui.creator.concept_match_review import render_concept_match_review
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


def archive_world(asset_id: str) -> None:
    """Soft-delete a World while preserving references for Stories/Universe."""
    ctx.assets.archive_world(asset_id)
    st.session_state.pop(f"confirm_delete_world_{asset_id}", None)
    if st.session_state.get("selected_world_id") == asset_id:
        st.session_state.pop("selected_world_id", None)


def explore_world(asset_id: str) -> None:
    """Open an approved Blueprint in the browser 3D runtime."""
    st.session_state.selected_world_id = asset_id
    st.session_state.app_page = "🎮 Explore World"


def edit_world(asset) -> None:
    """Load an existing Mini World back into its original creation path."""
    profile = WorldProfile.model_validate(
        asset.metadata.get("world_profile", {})
    )
    raw_scene_plan = asset.metadata.get("world_scene_plan") or {}
    source_mode = raw_scene_plan.get("source_mode", "custom")
    st.session_state.world_draft = profile
    st.session_state.world_source = asset.description or profile.source_description
    st.session_state.world_name = asset.display_name
    st.session_state.editing_world_id = asset.asset_id
    st.session_state.world_creation_mode = (
        "prompt" if source_mode == "prompt" else "custom"
    )
    st.session_state.world_stage = 4 if source_mode == "prompt" else 0
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
# Collapsible hierarchy keeps Creator navigation compact and scalable.
# ---------------------------------------------------------------------------

NAV_GROUPS = [
    (
        "🎭 Characters / 角色",
        ["🎭 My Characters", "✨ Character Factory"],
    ),
    (
        "🗺️ Worlds / 世界",
        ["🗺️ My Worlds", "🌍 World Factory", "🎮 Explore World"],
    ),
    (
        "🌎 Universe / 宇宙",
        ["🌎 Mini Utopia", "📖 Stories"],
    ),
    (
        "🧪 Sandbox / 实验",
        ["🧪 Playground"],
    ),
]

if "app_page" not in st.session_state:
    st.session_state.app_page = "🏠 Home"


def _go_sidebar_page(target_page: str) -> None:
    st.session_state.app_page = target_page


current_page = st.session_state.app_page

st.sidebar.markdown("### Navigate / 导航")
st.sidebar.button(
    "🏠 Home",
    key="nav_home",
    type="primary" if current_page == "🏠 Home" else "secondary",
    on_click=_go_sidebar_page,
    args=("🏠 Home",),
    use_container_width=True,
)

for group_label, group_pages in NAV_GROUPS:
    active_group = current_page in group_pages
    with st.sidebar.expander(group_label, expanded=active_group):
        for target_page in group_pages:
            st.button(
                target_page,
                key=f"nav_{target_page}",
                type="primary" if current_page == target_page else "secondary",
                on_click=_go_sidebar_page,
                args=(target_page,),
                use_container_width=True,
            )

page = st.session_state.app_page


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

    create_col, _ = st.columns([1, 3])
    with create_col:
        if st.button(
            "✨ Create Another Character / 再创造一个",
            use_container_width=True,
        ):
            reset_character_creation_state()
            st.session_state.pending_app_page = "✨ Character Factory"
            st.rerun()

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
            art_col, info_col = st.columns([1.0, 1.72], gap="large")

            with art_col:
                st.markdown('<div class="mu-character-art-shell">', unsafe_allow_html=True)
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
                st.markdown('</div>', unsafe_allow_html=True)

                edit_col, delete_col = st.columns(2)
                with edit_col:
                    st.button(
                        "✏️ Edit / 编辑",
                        key=f"edit_{asset.asset_id}",
                        on_click=edit_character,
                        args=(asset,),
                        use_container_width=True,
                    )
                with delete_col:
                    confirm_key = f"confirm_delete_{asset.asset_id}"
                    if not st.session_state.get(confirm_key):
                        if st.button(
                            "🗑️ Delete / 删除",
                            key=f"delete_{asset.asset_id}",
                            use_container_width=True,
                        ):
                            st.session_state[confirm_key] = True
                            st.rerun()

                if st.session_state.get(f"confirm_delete_{asset.asset_id}"):
                    st.warning("确定删除这个角色？")
                    yes_col, no_col = st.columns(2)
                    with yes_col:
                        if st.button(
                            "✅ Confirm",
                            key=f"confirm_delete_button_{asset.asset_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            archive_character(asset.asset_id)
                            st.rerun()
                    with no_col:
                        if st.button(
                            "↩ Cancel",
                            key=f"cancel_delete_{asset.asset_id}",
                            use_container_width=True,
                        ):
                            st.session_state[f"confirm_delete_{asset.asset_id}"] = False
                            st.rerun()

            with info_col:
                type_role = " · ".join(
                    part
                    for part in [profile.character_type, profile.story_role]
                    if part
                )
                personality_html = "".join(
                    f'<span class="mu-pill">{item}</span>'
                    for item in profile.personality_traits
                )
                st.markdown(
                    f'<div class="mu-character-name-row"><h3>{asset.display_name}</h3>'
                    f'<span class="mu-pill">v{asset.version}</span>{personality_html}</div>',
                    unsafe_allow_html=True,
                )
                if type_role:
                    st.caption(type_role)

                height_text = (
                    f"{profile.height_cm:.0f} cm"
                    if profile.height_cm is not None
                    else (profile.height or "—")
                )
                hair = profile.hair_style or profile.hair_or_fur or "—"
                build = profile.body_build or profile.body_type or "—"
                movement = profile.movement_style or "—"
                eyes = profile.eyes.color or "—"

                fact_rows = [
                    (("🗓️", "Age / 年龄", profile.age or "—"), ("📏", "Height / 身高", height_text)),
                    (("🧸", "Hair / Fur / 发型毛发", hair), ("👁️", "Eyes / 眼睛", eyes)),
                    (("🧊", "Build / 体型", build), ("🏃", "Movement / 动作", movement)),
                ]
                for left_fact, right_fact in fact_rows:
                    fact_a, fact_b = st.columns(2)
                    for col, fact in ((fact_a, left_fact), (fact_b, right_fact)):
                        with col:
                            icon, label, value = fact
                            st.markdown(
                                f'<div class="mu-character-fact-tile">'
                                f'<div class="mu-character-fact-label">{icon} {label}</div>'
                                f'<div class="mu-character-fact-value">{value}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                if profile.favorite_color_hexes:
                    swatches = "".join(
                        f'<span class="mu-color-dot" style="background:{hex_value}" '
                        f'title="{hex_value}"></span>'
                        for hex_value in profile.favorite_color_hexes
                    )
                    st.markdown(
                        f'<div class="mu-character-section-card">'
                        f'<strong>🎨 Favorite Colors / 喜爱颜色</strong>'
                        f'<div class="mu-color-row">{swatches}</div></div>',
                        unsafe_allow_html=True,
                    )

                if profile.distinctive_features:
                    distinctive = " · ".join(profile.distinctive_features)
                    st.markdown(
                        f'<div class="mu-character-section-card">'
                        f'<strong>⭐ Distinctive Feature / 标志特征</strong><br>'
                        f'{distinctive}</div>',
                        unsafe_allow_html=True,
                    )

                if asset.description:
                    st.caption(asset.description)

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
        "这些世界先由 Blueprint 确定结构，再用同一份 Blueprint 渲染视觉预览并进入 3D。",
        kicker="WORLD LIBRARY",
    )

    worlds = [
        asset
        for asset in ctx.repository.list_assets(AssetType.LOCATION)
        if ctx.assets.is_world_library_visible(asset)
    ]

    if not worlds:
        st.info("还没有 Mini World。去 World Factory 创造第一个世界吧！")

    for asset in worlds:
        profile = WorldProfile.model_validate(
            asset.metadata.get("world_profile", {})
        )
        pipeline = asset.metadata.get("world_pipeline", "legacy")
        world_visual = (
            ctx.world_concepts.current_preview(asset.asset_id)
            if pipeline == "blueprint_first_v1"
            else ctx.world_concepts.current_concept(asset.asset_id)
        )

        with st.container(border=True):
            art_col, info_col, action_col = st.columns([1.45, 2.15, 0.7])

            with art_col:
                if world_visual:
                    try:
                        st.image(
                            ctx.storage.get_bytes(world_visual.path),
                            caption=(
                                "✨ Blueprint World Preview"
                                if pipeline == "blueprint_first_v1"
                                else "✨ Approved World Concept"
                            ),
                            use_container_width=True,
                        )
                    except Exception:
                        st.markdown(
                            '<div class="mu-character-master-placeholder">🌍<br>'
                            '<span>World preview unavailable</span></div>',
                            unsafe_allow_html=True,
                        )
                elif asset.metadata.get("world_blueprint"):
                    st.markdown(
                        '<div class="mu-character-master-placeholder">🧩<br>'
                        '<span>Blueprint ready · preview not rendered yet</span></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="mu-character-master-placeholder">🏝️<br>'
                        '<span>World not built yet</span></div>',
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
                approved_concept = asset.metadata.get("world_concept_path")
                has_candidate = any(
                    file_ref.role == "world_concept_candidate"
                    for file_ref in asset.files
                )
                legacy_blueprint = bool(
                    pipeline != "blueprint_first_v1"
                    and blueprint
                    and approved_concept
                    and not (blueprint.get("layout_elements") or [])
                )
                if blueprint:
                    st.success("🎮 Ready to Explore / 可以进入世界")
                    st.caption("50×50 Mini World · Blueprint + Portal + Landmarks + Director Tour ready")
                    if (
                        pipeline == "blueprint_first_v1"
                        and not asset.metadata.get("world_preview_path")
                    ):
                        st.caption("🎨 World Preview 尚未渲染；不影响进入 3D 世界。")
                    if legacy_blueprint:
                        st.warning(
                            "🧩 Legacy Blueprint detected / 旧版 Blueprint："
                            "这个世界可以探索，但还没有 Concept Match Review 需要的新版布局数据。"
                        )
                        if st.button(
                            "🔄 Upgrade Blueprint / 升级可玩布局",
                            key=f"upgrade_world_blueprint_{asset.asset_id}",
                            disabled=not bool(universe.style_asset_id),
                            use_container_width=True,
                        ):
                            try:
                                with st.spinner("正在用已批准的 Concept 升级 Blueprint…"):
                                    ctx.world_concepts.rebuild_blueprint_from_current_concept(
                                        location_asset_id=asset.asset_id,
                                        style_asset_id=universe.style_asset_id,
                                    )
                                st.success("Blueprint 已升级，可以进行 Concept Match Review。")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Blueprint upgrade failed / 升级失败: {exc}")
                    if mode == "🛠 Studio" and studio_unlocked:
                        anchor = blueprint.get("visual_anchor", {}) or {}
                        with st.expander("🎯 Concept Visual Anchor", expanded=False):
                            st.write(
                                "**Must Preserve** · "
                                + (" · ".join(anchor.get("must_preserve", [])) or "—")
                            )
                            st.write(
                                "**Flexible Details** · "
                                + (" · ".join(anchor.get("flexible_details", [])) or "—")
                            )
                            if anchor.get("composition_notes"):
                                st.write(
                                    "**Composition** · "
                                    + " · ".join(anchor.get("composition_notes", []))
                                )
                            if anchor.get("spatial_relations"):
                                st.write(
                                    "**Spatial Relations** · "
                                    + " · ".join(anchor.get("spatial_relations", []))
                                )
                            layout_elements = blueprint.get("layout_elements", []) or []
                            if layout_elements:
                                st.write("**Compiled Layout / 已编译布局**")
                                for element in layout_elements:
                                    position = element.get("position", {}) or {}
                                    st.caption(
                                        f"{element.get('kind', 'landmark')} · "
                                        f"{element.get('name', 'Unnamed')} · "
                                        f"x={position.get('x', '—')}, z={position.get('z', '—')}"
                                    )
                            st.caption(
                                f"Extraction · {anchor.get('extraction_method', 'legacy')} · "
                                f"Direction · {anchor.get('concept_direction', '—')}"
                            )
                elif has_candidate:
                    st.warning("💖 Legacy Concept generated · please finish it in World Factory")
                else:
                    st.caption("🧩 Blueprint not built yet")

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

                confirm_world_key = f"confirm_delete_world_{asset.asset_id}"
                if not st.session_state.get(confirm_world_key):
                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_world_{asset.asset_id}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_world_key] = True
                        st.rerun()
                else:
                    st.warning("确定删除这个世界？")
                    if st.button(
                        "✅ Confirm",
                        key=f"confirm_delete_world_button_{asset.asset_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        archive_world(asset.asset_id)
                        st.rerun()
                    if st.button(
                        "↩ Cancel",
                        key=f"cancel_delete_world_{asset.asset_id}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_world_key] = False
                        st.rerun()

                st.caption(f"v{asset.version}")

            if (
                pipeline != "blueprint_first_v1"
                and blueprint
                and approved_concept
                and not legacy_blueprint
            ):
                render_concept_match_review(
                    ctx,
                    asset=asset,
                    studio_mode=bool(mode == "🛠 Studio" and studio_unlocked),
                )


elif page == "🎮 Explore World":
    render_game_hero(
        "Choose Your Adventure 🎮",
        "选一个 Mini World，再带一个角色进去。准备好以后，直接开始探索。",
        kicker="ENTER MINI UTOPIA",
    )

    playable_worlds = [
        asset
        for asset in ctx.repository.list_assets(AssetType.LOCATION)
        if ctx.assets.is_world_library_visible(asset)
        and asset.metadata.get("world_blueprint")
    ]

    if not playable_worlds:
        st.info("还没有可以进入的 Mini World。先去 World Factory 创造并选择一个世界吧！")
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

        world_col, traveler_col = st.columns(2, gap="large")
        with world_col:
            st.markdown(
                '<div class="mu-play-launch-card"><div class="mu-play-icon">🌍</div>'
                '<strong>Choose a World / 选择世界</strong>'
                '<span>从已经搭好的 Mini World 里选一个今天要去的地方。</span></div>',
                unsafe_allow_html=True,
            )
            selected = st.selectbox(
                "World",
                playable_worlds,
                index=selected_index,
                format_func=lambda asset: asset.display_name,
                label_visibility="collapsed",
            )
            st.session_state.selected_world_id = selected.asset_id
            profile = WorldProfile.model_validate(
                selected.metadata.get("world_profile", {})
            )
            selected_pipeline = selected.metadata.get("world_pipeline", "legacy")
            world_visual = (
                ctx.world_concepts.current_preview(selected.asset_id)
                if selected_pipeline == "blueprint_first_v1"
                else ctx.world_concepts.current_concept(selected.asset_id)
            )
            if world_visual:
                try:
                    st.image(
                        ctx.storage.get_bytes(world_visual.path),
                        caption=f"✨ {selected.display_name}",
                        use_container_width=True,
                    )
                except Exception:
                    st.caption("World preview 暂时无法读取。")

        playable_characters = [
            asset
            for asset in ctx.repository.list_assets(AssetType.CHARACTER)
            if asset.status == ReviewStatus.APPROVED
            and "character_profile" in asset.metadata
        ]
        selected_character = None
        character_profile = None
        character_runtime = ctx.character_runtime.resolve(None)

        with traveler_col:
            st.markdown(
                '<div class="mu-play-launch-card"><div class="mu-play-icon">🧸</div>'
                '<strong>Choose a Traveler / 选择角色</strong>'
                '<span>带一个已经确认过造型的角色进入这个世界。</span></div>',
                unsafe_allow_html=True,
            )
            if playable_characters:
                selected_character = st.selectbox(
                    "Traveler",
                    playable_characters,
                    format_func=lambda asset: asset.display_name,
                    key="runtime_character_asset",
                    label_visibility="collapsed",
                )
                character_profile = CharacterProfile.model_validate(
                    selected_character.metadata.get("character_profile", {})
                )
                character_runtime = ctx.character_runtime.resolve(selected_character)
                master_ref = ctx.character_masters.current_master(
                    selected_character.asset_id
                )
                if master_ref:
                    try:
                        st.image(
                            ctx.storage.get_bytes(master_ref.path),
                            caption=f"🧸 {selected_character.display_name}",
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption("Character Master preview 暂时无法读取。")
            else:
                st.info("还没有 Approved Character，会使用 Mini Traveler placeholder。")

        blueprint = WorldBlueprint.model_validate(
            selected.metadata.get("world_blueprint", {})
        )
        raw_render_spec = selected.metadata.get("world_render_spec")
        render_spec = (
            WorldRenderSpec.model_validate(raw_render_spec)
            if raw_render_spec
            else None
        )
        summary = runtime_summary(
            profile=profile,
            blueprint=blueprint,
            character_profile=character_profile,
        )

        st.markdown(
            '<div class="mu-ready-banner">🚪 Adventure Ready / 准备完成 · '
            '进入世界后用 WASD 或方向键移动，按住 Shift 奔跑。</div>',
            unsafe_allow_html=True,
        )

        a, b, c3, d = st.columns(4)
        a.metric("🗺️ World", summary["grid"])
        b.metric("🧩 Chunks", summary["chunks"])
        c3.metric("🏰 Landmarks", summary["landmarks"])
        d.metric("🎬 Tour Shots", summary["camera_points"])

        st.caption(
            f"Today: {selected_character.display_name if selected_character else 'Mini Traveler'} "
            f"→ {selected.display_name} · Portal and Director Tour are ready."
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
                render_spec=render_spec,
            ),
            height=760,
            scrolling=False,
        )

        st.caption(
            "🎮 Controls · WASD / Arrow Keys 移动 · Shift 奔跑 · "
            "右上角 Start Director Tour 自动参观世界。"
        )

        if mode == "🛠 Studio" and studio_unlocked:
            st.caption(
                f"Runtime · {character_runtime.mode.upper()} · "
                f"Idle / Walk / Run = "
                f"{character_runtime.animation_clips.idle} / "
                f"{character_runtime.animation_clips.walk} / "
                f"{character_runtime.animation_clips.run}"
            )
            with st.expander("🧩 Runtime Blueprint Inspector", expanded=False):
                st.json(blueprint.model_dump(mode="json"))
                if render_spec is not None:
                    st.markdown("**🎨 RenderSpec / Three.js contract**")
                    st.json(render_spec.model_dump(mode="json"))


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

        repository_backend = ctx.settings.studio_repository_backend
        if repository_backend == "supabase":
            st.success("🗄️ Durable Metadata Repository · Supabase Postgres")
            st.write(f"**Table** · {ctx.settings.supabase_metadata_table}")
            st.caption(
                "Character profiles, World profiles, Blueprints, Stories and runtime metadata "
                "are stored durably in Supabase."
            )
        else:
            st.warning("🗄️ Metadata Repository · SQLite / ephemeral on Streamlit Cloud")
            st.caption(
                "Character and World records can disappear across redeploys or restarts. "
                "Use STUDIO_REPOSITORY_BACKEND=supabase for durable metadata."
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
