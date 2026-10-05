from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from studio.models.world import WorldBlueprint, WorldProfile, WorldScenePlan
from studio.services.godot_hero_export_service import GodotHeroExportService
from studio.ui.creator.world_presets import (
    ARCHITECTURE_OPTIONS,
    LANDMARK_OPTIONS,
    LANDSCAPE_OPTIONS,
    MOOD_OPTIONS,
    PORTAL_OPTIONS,
    REALITY_MODE_OPTIONS,
    SEASON_OPTIONS,
    STORY_FUNCTION_OPTIONS,
    SURPRISE_OPTIONS,
    TERRAIN_OPTIONS,
    THEME_COLORS,
    TIME_OPTIONS,
    TRAVERSABILITY_OPTIONS,
    WATER_OPTIONS,
    WEATHER_OPTIONS,
    WORLD_TYPE_OPTIONS,
)
from studio.ui.creator.concept_match_review import _layout_svg
from studio.ui.theme import render_game_hero, render_quest


REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_GENERATIONS_PER_SESSION = 20
def _default_profile() -> WorldProfile:
    return WorldProfile(
        world_type=WORLD_TYPE_OPTIONS[0],
        reality_mode=REALITY_MODE_OPTIONS[0],
        story_function=STORY_FUNCTION_OPTIONS[0],
        terrain=[TERRAIN_OPTIONS[0]],
        season=SEASON_OPTIONS[0],
        weather=WEATHER_OPTIONS[0],
        time_of_day=TIME_OPTIONS[1],
        architecture=ARCHITECTURE_OPTIONS[0],
        water_features=[],
        landscape_elements=[LANDSCAPE_OPTIONS[0]],
        mood=[MOOD_OPTIONS[1]],
        landmark_ideas=[LANDMARK_OPTIONS[1]],
        portal_form=PORTAL_OPTIONS[0],
        traversability_notes=TRAVERSABILITY_OPTIONS[0],
        theme_color_hexes=[
            THEME_COLORS["Strawberry Pink"],
            THEME_COLORS["Mint"],
            THEME_COLORS["Lavender"],
        ],
        playable=True,
    )


def _safe_index(options: list[str], value: str, default: int = 0) -> int:
    try:
        return options.index(value)
    except ValueError:
        return default


def _clear_world_state() -> None:
    for key in (
        "world_draft",
        "world_source",
        "world_source_text",
        "world_name",
        "world_name_input",
        "world_creation_mode",
        "world_stage",
        "world_concept_candidates",
        "editing_world_id",
    ):
        st.session_state.pop(key, None)


def _reset_world() -> None:
    _clear_world_state()
    st.rerun()


def render_world_factory(
    ctx,
    *,
    style_asset_id: str | None,
    studio_mode: bool = False,
) -> None:
    """Blueprint-first World Factory with independent Prompt and Custom entry paths."""

    render_game_hero(
        "Build a Mini World 🌍",
        "先想象，再搭 Blueprint，再把同一个世界渲染出来。Prompt 和 Custom 最终走同一条可玩世界管线。",
        kicker="WORLD FACTORY · BLUEPRINT FIRST",
    )

    nav_col, _ = st.columns([1, 3])
    with nav_col:
        if st.button(
            "← Back to My Worlds / 返回我的世界",
            key="world_factory_back_to_library",
            use_container_width=True,
        ):
            _clear_world_state()
            st.session_state.pending_app_page = "🗺️ My Worlds"
            st.rerun()

    st.caption(
        "💾 Draft mode / 草稿模式：创建过程中可以随时离开；只有点击 Finish / 完成 后，"
        "这个 World 才会出现在 My Worlds 和 Explore World。"
    )

    draft: WorldProfile | None = st.session_state.get("world_draft")
    mode = st.session_state.get("world_creation_mode")

    if draft is None and mode is None:
        render_quest("你想怎么开始？ / How do you want to start?")
        left, right = st.columns(2)

        with left:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">✨📝</div>'
                '<h3>Prompt Generate</h3>'
                '<p>一句话描述 · GPT 理解、适度加入 Mini Utopia 元素，并直接规划 Scene Plan + Blueprint。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "✨ Prompt Generate / 描述生成",
                key="start_world_prompt",
                use_container_width=True,
            ):
                st.session_state.world_creation_mode = "prompt"
                st.rerun()

        with right:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">🎨🧩</div>'
                '<h3>Custom Build</h3>'
                '<p>自定义搭建 · 像搭积木一样，从预设选项一步步创造 Mini World。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "🎨 Custom Build / 自定义搭建",
                key="start_world_custom",
                use_container_width=True,
            ):
                st.session_state.world_creation_mode = "custom"
                st.session_state.world_draft = _default_profile()
                st.session_state.world_stage = 0
                st.rerun()
        return

    if draft is None and mode == "prompt":
        render_quest(
            "把脑海里的世界讲出来。GPT 会先忠实提取你要求的元素，再做少量 Mini Utopia "
            "风格补充，并直接规划探索与拍照路线；不会再让你重复填写 Custom Build。"
        )
        description = st.text_area(
            "Describe your world / 描述你的世界",
            value=st.session_state.get("world_source", ""),
            placeholder=(
                "例如：一个粉色漂浮岛世界，中央有湖，星星传送门在湖后面，"
                "右边有城堡，一座桥连接湖和城堡，周围有花和发光植物。"
            ),
            height=180,
            key="world_source_text",
        )
        if not ctx.world_scene_plans.prompt_available:
            st.info(
                "Structured text planning API 尚未连接。Prompt Generate 暂不可用，"
                "但 Custom Build 仍然可以使用。"
            )

        a, b = st.columns([2, 1])
        with a:
            if st.button(
                "✨ Plan & Build World / 生成世界蓝图",
                type="primary",
                disabled=(
                    not description.strip()
                    or not style_asset_id
                    or not ctx.world_scene_plans.prompt_available
                ),
                use_container_width=True,
            ):
                try:
                    style = ctx.repository.get_asset(style_asset_id)
                    if style is None:
                        raise RuntimeError("Mini Utopia Global Style Canon is missing.")
                    with st.spinner(
                        "🧠 正在理解你的世界、加入受控 Utopia 细节，并规划探索路线…"
                    ):
                        interpretation = ctx.world_scene_plans.plan_from_prompt(
                            description=description,
                            style_profile=style.metadata.get("style_profile", {}),
                        )
                        profile = interpretation.to_profile(
                            source_description=description
                        )
                        editing_id = st.session_state.get("editing_world_id")
                        if editing_id:
                            asset = ctx.assets.update_world(
                                asset_id=editing_id,
                                name=profile.world_name,
                                description=description,
                                profile=profile,
                            )
                        else:
                            asset = ctx.assets.create_world(
                                name=profile.world_name,
                                description=description,
                                profile=profile,
                            )
                        ctx.world_concepts.plan_blueprint(
                            location_asset_id=asset.asset_id,
                            style_asset_id=style_asset_id,
                            scene_plan=interpretation.scene_plan,
                        )

                    st.session_state.world_source = description
                    st.session_state.world_draft = profile
                    st.session_state.world_name = profile.world_name
                    st.session_state.editing_world_id = asset.asset_id
                    st.session_state.world_creation_mode = "prompt"
                    st.session_state.world_stage = 4
                    st.rerun()
                except Exception as exc:
                    st.error(f"Prompt planning failed / 世界规划失败: {exc}")
        with b:
            if st.button("← Back / 返回", use_container_width=True):
                st.session_state.world_creation_mode = None
                st.session_state.pop("editing_world_id", None)
                st.rerun()
        return

    draft = st.session_state.get("world_draft")
    if draft is None:
        return

    stages = [
        "1 · Identity / 身份",
        "2 · Environment / 环境",
        "3 · World Look / 视觉",
        "4 · Landmarks & Portal / 地标",
        "5 · Create / 生成",
    ]
    if mode == "prompt":
        stage = 4
        st.progress(
            1.0,
            text="Prompt → GPT Scene Plan → Blueprint · 完成结构规划",
        )
        st.caption(
            "Prompt 路线不会经过 Custom Build。下方可以检查 Scene Plan、Blueprint，再决定是否渲染 Preview。"
        )
    else:
        stage = max(0, min(int(st.session_state.get("world_stage", 0)), 4))
        st.progress((stage + 1) / 5, text=f"{stages[stage]} · {stage + 1}/5")
        st.caption("Custom Build：选择题优先，只有最后的 Extra Details 自由发挥。")

    def go(value: int) -> None:
        st.session_state.world_stage = max(0, min(value, 4))
        st.rerun()

    if stage == 0:
        st.markdown("### 🌐 Identity / 这是一个什么世界？")
        a, b = st.columns(2)
        with a:
            name = st.text_input(
                "World Name / 世界名字",
                value=st.session_state.get("world_name", draft.world_name),
                placeholder="例如：Candy Cloud Valley",
                key="world_name_input",
            )
            world_type = st.selectbox(
                "World Type / 世界类型",
                WORLD_TYPE_OPTIONS,
                index=_safe_index(WORLD_TYPE_OPTIONS, draft.world_type),
            )
        with b:
            reality = st.selectbox(
                "Reality / 世界属性",
                REALITY_MODE_OPTIONS,
                index=_safe_index(REALITY_MODE_OPTIONS, draft.reality_mode),
            )
            story_function = st.selectbox(
                "Story Function / 在故事里做什么？",
                STORY_FUNCTION_OPTIONS,
                index=_safe_index(STORY_FUNCTION_OPTIONS, draft.story_function),
            )

        if draft.source_description:
            st.info("✨ Prompt 已经保留。接下来只需要用选项把世界骨架确认清楚。")

        if st.button("Next → Environment", type="primary", use_container_width=True):
            st.session_state.world_name = name
            st.session_state.world_draft = draft.model_copy(
                update={
                    "world_name": name,
                    "world_type": world_type,
                    "reality_mode": reality,
                    "story_function": story_function,
                }
            )
            go(1)
        return

    if stage == 1:
        st.markdown("### 🏞️ Environment / 这个世界由什么组成？")
        a, b = st.columns(2)
        with a:
            terrain = st.multiselect(
                "Terrain / 地形（最多 4 个）",
                TERRAIN_OPTIONS,
                default=[x for x in draft.terrain if x in TERRAIN_OPTIONS][:4],
                max_selections=4,
            )
            season = st.selectbox(
                "Season / 季节",
                SEASON_OPTIONS,
                index=_safe_index(SEASON_OPTIONS, draft.season),
            )
            weather = st.selectbox(
                "Weather / 天气",
                WEATHER_OPTIONS,
                index=_safe_index(WEATHER_OPTIONS, draft.weather),
            )
        with b:
            time_of_day = st.selectbox(
                "Time / 时间",
                TIME_OPTIONS,
                index=_safe_index(TIME_OPTIONS, draft.time_of_day),
            )
            water = st.multiselect(
                "Water / 水体",
                WATER_OPTIONS,
                default=[x for x in draft.water_features if x in WATER_OPTIONS],
                max_selections=2,
            )
            landscape = st.multiselect(
                "Landscape Details / 环境细节",
                LANDSCAPE_OPTIONS,
                default=[x for x in draft.landscape_elements if x in LANDSCAPE_OPTIONS][:3],
                max_selections=3,
            )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", key="world_env_back", use_container_width=True):
                go(0)
        with nxt:
            if st.button("Next → World Look", type="primary", use_container_width=True):
                st.session_state.world_draft = draft.model_copy(
                    update={
                        "terrain": terrain,
                        "season": season,
                        "weather": weather,
                        "time_of_day": time_of_day,
                        "water_features": water,
                        "landscape_elements": landscape,
                    }
                )
                go(2)
        return

    if stage == 2:
        st.markdown("### 🎨 World Look / 它看起来是什么感觉？")
        a, b = st.columns(2)
        with a:
            mood = st.multiselect(
                "Mood / 氛围（最多 3 个）",
                MOOD_OPTIONS,
                default=[x for x in draft.mood if x in MOOD_OPTIONS][:3],
                max_selections=3,
            )
            architecture = st.selectbox(
                "Architecture / 建筑语言",
                ARCHITECTURE_OPTIONS,
                index=_safe_index(ARCHITECTURE_OPTIONS, draft.architecture),
            )
        with b:
            selected_colors = st.multiselect(
                "Theme Colors / 世界主题色（最多 5 个）",
                list(THEME_COLORS),
                default=[
                    name
                    for name, hex_value in THEME_COLORS.items()
                    if hex_value in draft.theme_color_hexes
                ][:5],
                max_selections=5,
            )
            color_hexes = [THEME_COLORS[name] for name in selected_colors]
            if color_hexes:
                swatches = "".join(
                    f'<span class="mu-color-dot" style="background:{value}" title="{value}"></span>'
                    for value in color_hexes
                )
                st.markdown(
                    f'<div class="mu-color-row">{swatches}</div>',
                    unsafe_allow_html=True,
                )
            st.caption("🔒 这些主题色仍然服从 Mini Utopia Global Style Canon。")

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", key="world_look_back", use_container_width=True):
                go(1)
        with nxt:
            if st.button("Next → Landmarks", type="primary", use_container_width=True):
                st.session_state.world_draft = draft.model_copy(
                    update={
                        "mood": mood,
                        "architecture": architecture,
                        "theme_color_hexes": color_hexes,
                    }
                )
                go(3)
        return

    if stage == 3:
        st.markdown("### 🏰🌀 Landmarks & Portal / 去哪里、怎么走？")
        a, b = st.columns(2)
        with a:
            landmarks = st.multiselect(
                "Landmarks / 地标（最多 4 个）",
                LANDMARK_OPTIONS,
                default=[x for x in draft.landmark_ideas if x in LANDMARK_OPTIONS][:4],
                max_selections=4,
            )
            portal = st.selectbox(
                "Portal / 传送门",
                PORTAL_OPTIONS,
                index=_safe_index(PORTAL_OPTIONS, draft.portal_form),
            )
        with b:
            traversability = st.selectbox(
                "Exploration Layout / 探索路线",
                TRAVERSABILITY_OPTIONS,
                index=_safe_index(TRAVERSABILITY_OPTIONS, draft.traversability_notes),
            )
            surprises = st.multiselect(
                "Surprise Elements / 惊喜元素（最多 3 个）",
                SURPRISE_OPTIONS,
                default=[x for x in draft.surprise_elements if x in SURPRISE_OPTIONS][:3],
                max_selections=3,
            )

        st.divider()
        extra = st.text_area(
            "✨ Extra Details / 额外补充",
            value=draft.creator_extra_details,
            placeholder="只有这里自由发挥：如果上面选了 Custom，或者有一定要出现的奇怪细节，都写在这里。",
            height=120,
            help="Custom Build 唯一的自由描述区。",
        )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", key="world_landmark_back", use_container_width=True):
                go(2)
        with nxt:
            if st.button("Next → Create", type="primary", use_container_width=True):
                st.session_state.world_draft = draft.model_copy(
                    update={
                        "landmark_ideas": landmarks,
                        "portal_form": portal,
                        "portal_placement_idea": "Place the Portal where it creates a memorable reveal.",
                        "traversability_notes": traversability,
                        "surprise_elements": surprises,
                        "creator_extra_details": extra,
                    }
                )
                go(4)
        return

    final_profile = draft
    name = st.session_state.get("world_name", final_profile.world_name).strip()

    st.markdown("### 🧩 Create / 先搭世界，再渲染")
    info, palette = st.columns([1.5, 1])
    with info:
        st.markdown(f"#### {name or 'New Mini World'}")
        st.write(f"**Type** · {final_profile.world_type or '—'}")
        st.write(f"**Reality** · {final_profile.reality_mode or '—'}")
        st.write(f"**Terrain** · {', '.join(final_profile.terrain) or '—'}")
        st.write(f"**Mood** · {' · '.join(final_profile.mood) or '—'}")
        st.write(f"**Portal** · {final_profile.portal_form or '—'}")
        if final_profile.creator_extra_details:
            st.caption("Extra · " + final_profile.creator_extra_details)
    with palette:
        st.markdown("#### 🎨 Global Style + Theme")
        swatches = "".join(
            f'<span style="display:inline-block;width:34px;height:34px;'
            f'border-radius:12px;background:{color};margin:4px;'
            f'border:1px solid rgba(0,0,0,.08)"></span>'
            for color in final_profile.theme_color_hexes[:5]
        )
        st.markdown(swatches, unsafe_allow_html=True)
        st.caption("🔒 Mini Utopia Global Style Canon")
        st.caption("🧩 Initial playable target · 50×50 · 25 chunks")

    if not name:
        st.warning("请返回 Identity 给这个世界取一个名字。")

    editing_id = st.session_state.get("editing_world_id")
    saved_world = ctx.repository.get_asset(editing_id) if editing_id else None
    raw_blueprint = (
        saved_world.metadata.get("world_blueprint")
        if saved_world is not None
        else None
    )
    blueprint = (
        WorldBlueprint.model_validate(raw_blueprint)
        if raw_blueprint
        else None
    )
    raw_scene_plan = (
        saved_world.metadata.get("world_scene_plan")
        if saved_world is not None
        else None
    )
    scene_plan = (
        WorldScenePlan.model_validate(raw_scene_plan)
        if raw_scene_plan
        else None
    )
    desired_profile = final_profile.model_copy(update={"world_name": name})
    saved_profile = (
        WorldProfile.model_validate(saved_world.metadata.get("world_profile", {}))
        if saved_world is not None
        else None
    )
    profile_changed = bool(
        saved_profile is not None
        and desired_profile.model_dump(mode="json")
        != saved_profile.model_dump(mode="json")
    )
    blueprint_first_current = bool(
        saved_world is not None
        and blueprint is not None
        and saved_world.metadata.get("world_pipeline") == "blueprint_first_v1"
        and scene_plan is not None
        and blueprint.layout_elements
        and not profile_changed
    )

    st.markdown("#### 1 · Scene Plan → Blueprint / 先理解，再搭世界")
    st.caption(
        "Scene Plan 先确认世界里有什么、彼此关系和探索顺序；Blueprint 再把它变成精确可玩的 50×50 结构。"
        " World Preview 只负责把这个已经确定的世界画漂亮。"
    )

    if mode == "prompt":
        if st.button(
            "← Modify Prompt / 修改描述并重新规划",
            use_container_width=True,
        ):
            st.session_state.world_draft = None
            st.session_state.world_stage = 4
            st.rerun()
    else:
        back, plan_col = st.columns([1, 2])
        with back:
            if st.button("← Back to Edit", use_container_width=True):
                go(3)
        with plan_col:
            plan_label = (
                "🔄 Rebuild Playable Blueprint / 重建可玩蓝图"
                if blueprint is not None
                else "🧩 Build Playable Blueprint / 生成可玩蓝图"
            )
            if st.button(
                plan_label,
                type="primary",
                disabled=not bool(name and style_asset_id),
                use_container_width=True,
            ):
                try:
                    st.session_state.world_draft = desired_profile
                    style = ctx.repository.get_asset(style_asset_id)
                    if style is None:
                        raise RuntimeError("Mini Utopia Global Style Canon is missing.")
                    scene_plan_for_build = ctx.world_scene_plans.plan_from_profile(
                        profile=desired_profile,
                        style_profile=style.metadata.get("style_profile", {}),
                    )
                    if editing_id:
                        asset = ctx.assets.update_world(
                            asset_id=editing_id,
                            name=name,
                            description=desired_profile.source_description,
                            profile=desired_profile,
                        )
                    else:
                        asset = ctx.assets.create_world(
                            name=name,
                            description=desired_profile.source_description,
                            profile=desired_profile,
                        )
                        st.session_state.editing_world_id = asset.asset_id

                    ctx.world_concepts.plan_blueprint(
                        location_asset_id=asset.asset_id,
                        style_asset_id=style_asset_id,
                        scene_plan=scene_plan_for_build,
                    )
                    st.success("Scene Plan + Playable Blueprint ready / 世界规划与可玩蓝图已生成。")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Blueprint planning failed / 蓝图生成失败: {exc}")

    if scene_plan is not None:
        st.markdown("#### 🧠 Scene Plan / 世界清单")
        st.caption(
            "Creator Required 是你明确要求、必须保留的内容；Utopia Enrichment 是系统为品牌感、"
            "探索感和拍照体验加入的少量可调整细节。"
        )
        required_col, enrich_col = st.columns(2)
        with required_col:
            st.markdown("**🔒 Creator / Required**")
            required_items = [
                item
                for item in scene_plan.elements
                if item.source != "utopia_enrichment"
            ]
            for item in required_items:
                hint = f" · {item.placement_hint}" if item.placement_hint else ""
                st.write(
                    f"• **{item.name}** · {item.kind} · "
                    f"{item.spatial_mode}/{item.geometry_role}{hint}"
                )
        with enrich_col:
            st.markdown("**✨ Mini Utopia Enrichment**")
            enrichment = [
                item
                for item in scene_plan.elements
                if item.source == "utopia_enrichment"
            ]
            if enrichment:
                for item in enrichment:
                    st.write(
                        f"• **{item.name}** · {item.kind} · "
                        f"{item.spatial_mode}/{item.geometry_role}"
                    )
            else:
                st.caption("No extra enrichment / 没有额外补充")

        by_scene_id = {item.scene_id: item for item in scene_plan.elements}
        route_names = [
            by_scene_id[scene_id].name
            for scene_id in scene_plan.exploration_order
            if scene_id in by_scene_id
        ]
        if route_names:
            st.write("**🚶 Exploration Route / 探索路线**")
            st.caption(" → ".join(["Spawn / 出生点", *route_names]))
        if scene_plan.route_intent:
            st.caption("🎬 " + scene_plan.route_intent)

    if blueprint is not None:
        if profile_changed:
            st.warning(
                "⚠️ World Profile 已修改，但当前 Blueprint 还是旧版本。"
                " 请先 Rebuild Blueprint，避免丢失这次修改。"
            )
        elif not blueprint_first_current:
            st.warning(
                "🧩 这是旧版 Blueprint。进入新的 Blueprint-first 流程前，"
                "请先 Rebuild Blueprint。"
            )

        st.markdown("#### 🗺️ Playable Blueprint / 可玩蓝图")
        map_col, detail_col = st.columns([1.2, 1])
        with map_col:
            components.html(_layout_svg(blueprint), height=430, scrolling=False)
        with detail_col:
            st.caption(
                f"50×50 · {len(blueprint.layout_elements)} layout elements · "
                f"{len(blueprint.landmarks)} landmarks"
            )
            for element in blueprint.layout_elements[:10]:
                st.write(
                    f"**{element.name}** · {element.kind} · "
                    f"{element.spatial_mode}/{element.geometry_role} · "
                    f"x={element.position.x:.1f}, y={element.position.y:.1f}, "
                    f"z={element.position.z:.1f}"
                )
            st.caption(
                "这里的结构才是 3D Runtime 的 source of truth。"
                " 以后即使 Preview 图片有小偏差，也不会改写 Blueprint。"
            )

        st.markdown("#### 2 · World Preview / 根据 Blueprint 渲染一张世界图")
        current_preview = (
            ctx.world_concepts.current_preview(saved_world.asset_id)
            if blueprint_first_current
            else None
        )
        if current_preview:
            try:
                st.image(
                    ctx.storage.get_bytes(current_preview.path),
                    caption="✨ Blueprint World Preview",
                    use_container_width=True,
                )
            except Exception:
                st.caption("World Preview 暂时无法读取。")

        appearance_diagnostics = (
            saved_world.metadata.get("world_appearance_diagnostics", {})
            if saved_world is not None
            else {}
        )
        render_diagnostics = (
            saved_world.metadata.get("world_render_diagnostics", {})
            if saved_world is not None
            else {}
        )
        if appearance_diagnostics or render_diagnostics:
            with st.expander("🧪 3D Build Check / 外观与 RenderSpec 检查", expanded=False):
                st.caption(
                    "这里显示 GPT/Vision 实际给 Three.js 的外观部件。"
                    " Hero 如果仍是 0 parts，就不是 Three.js 丢了，而是上游外观没有生成完整。"
                )
                source = saved_world.metadata.get("world_appearance_source", "—")
                weak_count = appearance_diagnostics.get("weak_hero_count", 0)
                st.write(f"**Appearance Source** · {source}")
                planning_status = saved_world.metadata.get(
                    "world_appearance_generation_status", ""
                )
                if planning_status == "fallback":
                    fallback_source = saved_world.metadata.get(
                        "world_appearance_generation_fallback", "safe_fallback"
                    )
                    st.warning(
                        "GPT AppearancePlan fallback · "
                        f"{fallback_source} · build continued safely"
                    )
                st.write(f"**Weak Hero Objects** · {weak_count}")
                render_by_id = {
                    item.get("element_id"): item
                    for item in render_diagnostics.get("objects", [])
                }
                for item in appearance_diagnostics.get("objects", []):
                    if (
                        item.get("geometry_role") != "organic"
                        and item.get("part_count", 0) == 0
                    ):
                        continue
                    rendered = render_by_id.get(item.get("element_id"), {})
                    roles = ", ".join(item.get("part_roles", [])) or "—"
                    st.write(
                        f"**{item.get('name', 'Unnamed')}** · "
                        f"{item.get('silhouette_family', '—')} · "
                        f"main={item.get('main_primitive', '—')} · "
                        f"parts={item.get('part_count', 0)} [{roles}] · "
                        f"Three.js nodes={rendered.get('node_count', 0)}"
                    )

                composition = saved_world.metadata.get(
                    "world_hero_composition_plan", {}
                )
                clusters = composition.get("clusters", []) if composition else []
                if clusters:
                    st.divider()
                    st.write("**🧩 Unified Hero Composition / 整体 Hero 渲染**")
                    st.caption(
                        "Hero 内部对象保留 Blueprint 语义 ID，但渲染时不拆开；"
                        "整个 Hero Cluster 将使用同一 Reference、同一 GLB。"
                    )
                    element_names = {
                        element.element_id: element.name
                        for element in blueprint.layout_elements
                    }
                    for cluster in clusters:
                        root_id = cluster.get("root_element_id", "")
                        root_name = element_names.get(root_id, root_id or "Hero")
                        baked = [
                            element_names.get(
                                item.get("element_id"),
                                item.get("element_id"),
                            )
                            for item in cluster.get("members", [])
                            if item.get("role") == "baked"
                        ]
                        st.write(
                            f"**{root_name}** · "
                            f"{cluster.get('render_strategy', 'unified_glb')}"
                        )
                        st.caption(
                            "Baked together / 整体生成 · "
                            + (", ".join(baked) if baked else "仅 Root")
                        )

                hero_diagnostics = saved_world.metadata.get(
                    "world_hero_asset_diagnostics", []
                )
                if hero_diagnostics:
                    st.divider()
                    st.write("**🧊 Hero 3D Assets / Open-source GLB**")
                    for hero in hero_diagnostics:
                        status = hero.get("status", "—")
                        model = hero.get("model") or "—"
                        byte_count = int(hero.get("bytes", 0) or 0)
                        size_mb = byte_count / (1024 * 1024)
                        message = hero.get("message", "")
                        reference_mode = hero.get("reference_mode") or "—"
                        st.write(
                            f"**{hero.get('name', hero.get('element_id', 'Hero'))}** · "
                            f"{status} · model={model} · {size_mb:.2f} MB"
                        )
                        st.caption(f"Reference · {reference_mode}")
                        usage = hero.get("usage") or {}
                        if usage.get("status") == "ok":
                            remaining = float(
                                usage.get("remaining_seconds", 0) or 0
                            )
                            base = float(usage.get("base_seconds", 0) or 0)
                            if usage.get("kind") == "snapshot":
                                used = float(usage.get("used_seconds", 0) or 0)
                                st.caption(
                                    "HF ZeroGPU · "
                                    f"当前已用 {used/60:.1f}/{base/60:.1f} min · "
                                    f"剩余 {remaining/60:.1f} min"
                                )
                            else:
                                gpu_seconds = float(
                                    usage.get("gpu_seconds", 0) or 0
                                )
                                wall_seconds = float(
                                    usage.get("wall_seconds", 0) or 0
                                )
                                overquota = float(
                                    usage.get("overquota_gpu_seconds", 0) or 0
                                )
                                st.caption(
                                    "HF ZeroGPU · "
                                    f"本次 {gpu_seconds/60:.2f} GPU min · "
                                    f"墙钟 {wall_seconds/60:.2f} min · "
                                    f"剩余 {remaining/60:.1f}/{base/60:.1f} min"
                                    + (
                                        f" · paid {overquota/60:.2f} min"
                                        if overquota > 0
                                        else ""
                                    )
                                )
                        elif usage:
                            st.caption(
                                "HF ZeroGPU usage · "
                                f"{usage.get('status', 'unavailable')}"
                            )
                        cluster_id = hero.get("cluster_id") or ""
                        member_ids = hero.get("member_element_ids") or []
                        target_size = hero.get("target_size")
                        if cluster_id:
                            member_names = [
                                element_names.get(element_id, element_id)
                                for element_id in member_ids
                            ]
                            st.caption(
                                f"Unified Cluster · {cluster_id} · "
                                + ", ".join(member_names)
                            )
                            if target_size and len(target_size) >= 3:
                                st.caption(
                                    "Cluster Envelope · "
                                    f"{float(target_size[0]):.1f} × "
                                    f"{float(target_size[1]):.1f} × "
                                    f"{float(target_size[2]):.1f}"
                                )
                        if hero.get("asset_path"):
                            st.caption(f"GLB · {hero.get('asset_path')}")
                            hero_element = next(
                                (
                                    element
                                    for element in blueprint.layout_elements
                                    if element.element_id == hero.get("element_id")
                                ),
                                None,
                            )
                            bundle_key = (
                                f"godot_hero_bundle_{saved_world.asset_id}_"
                                f"{hero.get('element_id', 'hero')}"
                            )
                            if st.button(
                                "🎮 Prepare Godot Hero Bundle / 导出到 Godot",
                                key=f"prepare_{bundle_key}",
                                use_container_width=True,
                            ):
                                try:
                                    if hero_element is None:
                                        raise ValueError(
                                            "Hero Blueprint element is missing."
                                        )
                                    bundle = GodotHeroExportService(
                                        ctx.storage
                                    ).build_bundle(
                                        hero=hero,
                                        target_size=(
                                            tuple(float(value) for value in target_size[:3])
                                            if target_size and len(target_size) >= 3
                                            else (
                                                float(hero_element.width),
                                                float(hero_element.height),
                                                float(hero_element.depth),
                                            )
                                        ),
                                    )
                                    st.session_state[bundle_key] = {
                                        "filename": bundle.filename,
                                        "payload": bundle.payload,
                                    }
                                except Exception as exc:
                                    st.error(
                                        f"Godot Hero bundle failed: {exc}"
                                    )
                            prepared = st.session_state.get(bundle_key)
                            if prepared:
                                prepared_bundle = GodotHeroExportService(
                                    ctx.storage
                                ).build_bundle(
                                    hero=hero,
                                    target_size=(
                                        tuple(float(value) for value in target_size[:3])
                                        if target_size and len(target_size) >= 3
                                        else (
                                            float(hero_element.width),
                                            float(hero_element.height),
                                            float(hero_element.depth),
                                        )
                                    ),
                                )
                                local_checkout_ready = (
                                    (REPO_ROOT / ".git").exists()
                                    and (REPO_ROOT / "godot" / "project.godot").exists()
                                )
                                if local_checkout_ready:
                                    if st.button(
                                        "⚡ Install directly into local Godot / 一键装入 Godot",
                                        key=f"install_{bundle_key}",
                                        use_container_width=True,
                                    ):
                                        try:
                                            installed = GodotHeroExportService(
                                                ctx.storage
                                            ).install_bundle(
                                                bundle=prepared_bundle,
                                                repository_root=REPO_ROOT,
                                            )
                                            st.success(
                                                "Installed to local Godot · "
                                                f"{installed.hero_path.name} + "
                                                "hero_manifest.json"
                                            )
                                            st.caption(
                                                "Godot 会自动检测文件；"
                                                "如果已打开项目，等待 Import 完成后直接 Run。"
                                            )
                                        except Exception as exc:
                                            st.error(
                                                f"Local Godot install failed: {exc}"
                                            )
                                st.download_button(
                                    "⬇️ Download Godot Hero Bundle",
                                    data=prepared["payload"],
                                    file_name=prepared["filename"],
                                    mime="application/zip",
                                    key=f"download_{bundle_key}",
                                    use_container_width=True,
                                )
                                st.caption(
                                    "Download 是 Cloud/手动 fallback。"
                                    "本地运行 Streamlit 时优先使用一键安装。"
                                )
                                if reference_mode == "generated_unified_cluster_v1":
                                    st.success(
                                        "这是 Unified Hero Cluster GLB："
                                        "Godot 会把完整 Hero 作为一个主体加载，不做拆分重组。"
                                    )
                                elif reference_mode in {
                                    "generated_isolated_v1",
                                    "preview_bbox_isolated_v1",
                                }:
                                    st.info(
                                        "这份 GLB 可用于验证 Godot Runtime 通路，"
                                        "但它仍可能是旧的单对象 Hero。请重新 Render Preview "
                                        "生成 Unified Hero Cluster 后再作为最终资产使用。"
                                    )
                        if message:
                            st.warning(message)

                if studio_mode and saved_world is not None:
                    hero_candidates = [
                        element
                        for element in blueprint.layout_elements
                        if (
                            element.geometry_role == "organic"
                            and element.kind in {"landmark", "structure"}
                        )
                    ]
                    if hero_candidates:
                        st.divider()
                        st.write("**🛠 Manual Hero GLB Test / 手动验证**")
                        st.caption(
                            "可以先在 Pixal3D / TripoSR 官方 Demo 生成 GLB，"
                            "上传这里验证 GLB → RenderSpec → Three.js → Blueprint 回填。"
                        )
                        selected_hero = st.selectbox(
                            "Hero Blueprint Object",
                            hero_candidates,
                            format_func=lambda item: (
                                f"{item.name} · {item.element_id}"
                            ),
                            key=f"manual_hero_target_{saved_world.asset_id}",
                        )
                        manual_glb = st.file_uploader(
                            "Hero GLB",
                            type=["glb"],
                            key=f"manual_hero_glb_{saved_world.asset_id}",
                        )
                        if st.button(
                            "🧊 Attach Hero GLB / 接入 3D",
                            key=f"attach_hero_glb_{saved_world.asset_id}",
                            disabled=manual_glb is None,
                            use_container_width=True,
                        ):
                            try:
                                build = ctx.world_concepts.attach_manual_hero_glb(
                                    location_asset_id=saved_world.asset_id,
                                    element_id=selected_hero.element_id,
                                    payload=manual_glb.getvalue(),
                                )
                                st.success(
                                    f"Hero GLB attached · {build.name} · "
                                    f"{build.bytes / (1024 * 1024):.2f} MB"
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Hero GLB attach failed: {exc}")

        if getattr(ctx, "world_hero_assets", None) is not None:
            if ctx.world_hero_assets.is_available:
                provider = ctx.world_hero_assets.provider
                provider_name = (
                    f"Hugging Face · {getattr(provider, 'space_id', '')}"
                    if getattr(provider, "space_id", "")
                    else provider.__class__.__name__
                )
                st.caption(
                    "🧊 Hero GLB Provider 已连接 · "
                    f"{provider_name} · Render Preview 时会把最大的 organic Hero "
                    "送去 3D Asset Provider；已有精确缓存会直接复用。"
                )
            else:
                st.caption(
                    "🧩 Hero GLB Provider 未连接 · 当前 Explore 会继续使用 Procedural "
                    "Shape Grammar fallback。"
                )

        count = int(st.session_state.get("creator_generation_count", 0))
        remaining = max(0, MAX_GENERATIONS_PER_SESSION - count)
        st.caption(f"🎟️ 本次会话剩余图片渲染次数：{remaining}/{MAX_GENERATIONS_PER_SESSION}")

        render_col, finish_col = st.columns([2, 1])
        with render_col:
            if st.button(
                "🎨 Render World Preview / 渲染世界预览",
                type="primary",
                disabled=(
                    not blueprint_first_current
                    or not ctx.world_concepts.is_available
                    or not style_asset_id
                    or remaining < 1
                ),
                use_container_width=True,
            ):
                build_status = st.status(
                    "✨ Mini Utopia 正在开始建造这个世界…",
                    expanded=True,
                )
                build_progress = st.progress(
                    0,
                    text="🗺️ 正在读取 Blueprint…",
                )
                seen_stages: set[str] = set()

                def on_world_build_progress(
                    stage: str,
                    message: str,
                    progress: float,
                ) -> None:
                    percent = int(round(max(0.0, min(1.0, progress)) * 100))
                    build_progress.progress(percent, text=message)
                    build_status.update(
                        label=message,
                        state="running",
                        expanded=True,
                    )
                    if stage not in seen_stages:
                        build_status.write(message)
                        seen_stages.add(stage)

                try:
                    ctx.world_concepts.render_blueprint_preview(
                        location_asset_id=saved_world.asset_id,
                        style_asset_id=style_asset_id,
                        progress_callback=on_world_build_progress,
                    )
                    build_progress.progress(
                        100,
                        text="🌟 世界准备好了！可以进入 Preview 和 3D 世界。",
                    )
                    build_status.update(
                        label="🌟 World Ready / 世界建造完成",
                        state="complete",
                        expanded=False,
                    )
                    st.session_state.creator_generation_count = count + 1
                    st.rerun()
                except Exception as exc:
                    build_status.update(
                        label="🛠️ Build paused / 世界建造中断",
                        state="error",
                        expanded=True,
                    )
                    st.error(f"World Preview render failed / 渲染失败: {exc}")

        with finish_col:
            if st.button(
                "✅ Finish / 完成",
                disabled=profile_changed,
                use_container_width=True,
            ):
                if saved_world is not None:
                    ctx.assets.complete_world(saved_world.asset_id)
                _clear_world_state()
                st.session_state.pending_app_page = "🗺️ My Worlds"
                st.rerun()

        if not ctx.world_concepts.is_available:
            st.info(
                "Image API 尚未连接；Blueprint 已经可以直接 Explore，"
                "World Preview 可以以后再渲染。"
            )
    else:
        st.info(
            "先生成 Blueprint。生成后这个世界已经可以进入 3D；"
            "World Preview 是随后的一张视觉表达，不再决定结构。"
        )

    st.divider()
    if st.button("🆕 Start a New World / 新世界"):
        _reset_world()
