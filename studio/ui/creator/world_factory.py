from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from studio.models.world import WorldBlueprint, WorldProfile
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


MAX_GENERATIONS_PER_SESSION = 20
DIRECTION_LABELS = {
    "playable": "🧭 Playable / 清晰可探索",
    "dream": "✨ Dream / 最梦幻",
    "story": "📖 Story / 最有故事感",
}


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


def _draft_from_prompt(description: str) -> WorldProfile:
    """Seed the structured builder from a child's description.

    M2.1 keeps this deterministic and transparent. The original description is
    always preserved and drives Concept Art. Later a structured-text provider
    can improve the seeding without changing the UI or WorldProfile contract.
    """
    draft = _default_profile()
    text = description.lower()

    def choose(current: str, mapping: list[tuple[tuple[str, ...], str]]) -> str:
        for keywords, option in mapping:
            if any(keyword in text for keyword in keywords):
                return option
        return current

    world_type = choose(
        draft.world_type,
        [
            (("cloud", "云"), "Cloud Village / 云端小镇"),
            (("candy", "糖果"), "Candy Forest / 糖果森林"),
            (("star", "星"), "Star Harbor / 星光港湾"),
            (("mushroom", "蘑菇"), "Mushroom Valley / 蘑菇秘境"),
            (("underwater", "海底"), "Underwater Utopia / 海底乌托邦"),
            (("future", "未来"), "Future City / 未来城市"),
            (("floating", "漂浮"), "Floating Islands / 漂浮岛"),
        ],
    )
    time_of_day = choose(
        draft.time_of_day,
        [
            (("night", "夜"), "Night / 夜晚"),
            (("sunset", "日落"), "Sunset / 日落"),
            (("morning", "清晨"), "Morning / 清晨"),
        ],
    )
    mood = list(draft.mood)
    if any(k in text for k in ("mystery", "mysterious", "神秘")):
        mood = ["Mysterious / 神秘"]
    elif any(k in text for k in ("happy", "joy", "快乐")):
        mood = ["Joyful / 快乐"]

    return draft.model_copy(
        update={
            "source_description": description,
            "world_type": world_type,
            "time_of_day": time_of_day,
            "mood": mood,
        }
    )


def _reset_world() -> None:
    for key in (
        "world_draft",
        "world_source",
        "world_name",
        "world_name_input",
        "world_creation_mode",
        "world_stage",
        "world_concept_candidates",
        "editing_world_id",
    ):
        st.session_state.pop(key, None)
    st.rerun()


def render_world_factory(ctx, *, style_asset_id: str | None) -> None:
    """World Factory M2.1: same interaction grammar as Character Factory."""

    render_game_hero(
        "Build a Mini World 🌍",
        "先想象，再搭 Blueprint，再把同一个世界渲染出来。Prompt 和 Custom 最终走同一条可玩世界管线。",
        kicker="WORLD FACTORY · BLUEPRINT FIRST",
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
                '<p>描述生成 · 把脑海里的世界讲出来，系统先整理，再让你一步步确认。</p></div>',
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
        render_quest("把脑海里的世界讲出来。原始描述会一直保留，并成为 Concept Art 的创意核心。")
        description = st.text_area(
            "Describe your world / 描述你的世界",
            value=st.session_state.get("world_source", ""),
            placeholder=(
                "例如：一个只有晚上才会出现的云朵村，房子睡着以后屋顶会长出星星，"
                "桥下面有会发光的鲸鱼……"
            ),
            height=160,
            key="world_source_text",
        )
        a, b = st.columns([2, 1])
        with a:
            if st.button(
                "✨ Build My World / 帮我整理",
                type="primary",
                disabled=not description.strip(),
                use_container_width=True,
            ):
                st.session_state.world_source = description
                st.session_state.world_draft = _draft_from_prompt(description)
                st.session_state.world_creation_mode = "custom"
                st.session_state.world_stage = 0
                st.rerun()
        with b:
            if st.button("← Back / 返回", use_container_width=True):
                st.session_state.world_creation_mode = None
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
    stage = max(0, min(int(st.session_state.get("world_stage", 0)), 4))
    st.progress((stage + 1) / 5, text=f"{stages[stage]} · {stage + 1}/5")
    st.caption("和 Character Factory 一样：选择题优先，只有最后的 Extra Details 自由发挥。")

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

    st.markdown("#### 1 · Blueprint / 先确定世界结构")
    st.caption(
        "Blueprint 决定这个世界里有什么、在哪里、怎么走。"
        " World Preview 只负责把这个已经确定的世界画漂亮。"
    )

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
                final_profile = final_profile.model_copy(update={"world_name": name})
                st.session_state.world_draft = final_profile
                if editing_id:
                    asset = ctx.assets.update_world(
                        asset_id=editing_id,
                        name=name,
                        description=final_profile.source_description,
                        profile=final_profile,
                    )
                else:
                    asset = ctx.assets.create_world(
                        name=name,
                        description=final_profile.source_description,
                        profile=final_profile,
                    )
                    st.session_state.editing_world_id = asset.asset_id

                ctx.world_concepts.plan_blueprint(
                    location_asset_id=asset.asset_id,
                    style_asset_id=style_asset_id,
                )
                st.success("Playable Blueprint ready / 可玩蓝图已生成。")
                st.rerun()
            except Exception as exc:
                st.error(f"Blueprint planning failed / 蓝图生成失败: {exc}")

    if blueprint is not None:
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
                    f"x={element.position.x:.1f}, z={element.position.z:.1f}"
                )
            st.caption(
                "这里的结构才是 3D Runtime 的 source of truth。"
                " 以后即使 Preview 图片有小偏差，也不会改写 Blueprint。"
            )

        st.markdown("#### 2 · World Preview / 根据 Blueprint 渲染一张世界图")
        current_preview = ctx.world_concepts.current_concept(saved_world.asset_id)
        if current_preview:
            try:
                st.image(
                    ctx.storage.get_bytes(current_preview.path),
                    caption="✨ Blueprint World Preview",
                    use_container_width=True,
                )
            except Exception:
                st.caption("World Preview 暂时无法读取。")

        count = int(st.session_state.get("creator_generation_count", 0))
        remaining = max(0, MAX_GENERATIONS_PER_SESSION - count)
        st.caption(f"🎟️ 本次会话剩余图片渲染次数：{remaining}/{MAX_GENERATIONS_PER_SESSION}")

        render_col, finish_col = st.columns([2, 1])
        with render_col:
            if st.button(
                "🎨 Render World Preview / 渲染世界预览",
                type="primary",
                disabled=(
                    not ctx.world_concepts.is_available
                    or not style_asset_id
                    or remaining < 1
                ),
                use_container_width=True,
            ):
                try:
                    with st.spinner("🌈 正在按照 Blueprint 渲染这个世界…"):
                        ctx.world_concepts.render_blueprint_preview(
                            location_asset_id=saved_world.asset_id,
                            style_asset_id=style_asset_id,
                        )
                    st.session_state.creator_generation_count = count + 1
                    st.rerun()
                except Exception as exc:
                    st.error(f"World Preview render failed / 渲染失败: {exc}")

        with finish_col:
            if st.button(
                "✅ Finish / 完成",
                use_container_width=True,
            ):
                st.session_state.world_concept_candidates = []
                st.session_state.editing_world_id = None
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
