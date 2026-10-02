from __future__ import annotations

import streamlit as st

from studio.models.world import WorldProfile
from studio.ui.creator.world_presets import (
    LANDMARK_OPTIONS,
    MOOD_OPTIONS,
    PORTAL_OPTIONS,
    REALITY_MODE_OPTIONS,
    SEASON_OPTIONS,
    TERRAIN_OPTIONS,
    THEME_COLORS,
    TIME_OPTIONS,
    WEATHER_OPTIONS,
    WORLD_TYPE_OPTIONS,
)


MAX_GENERATIONS_PER_SESSION = 20
DIRECTION_LABELS = {
    "playable": "🧭 Playable / 清晰可探索",
    "dream": "✨ Dream / 最梦幻",
    "story": "📖 Story / 最有故事感",
}


def _default_profile() -> WorldProfile:
    return WorldProfile(
        world_name="",
        world_type=WORLD_TYPE_OPTIONS[0],
        reality_mode=REALITY_MODE_OPTIONS[0],
        terrain=[TERRAIN_OPTIONS[0]],
        season=SEASON_OPTIONS[0],
        weather=WEATHER_OPTIONS[0],
        time_of_day=TIME_OPTIONS[1],
        mood=[MOOD_OPTIONS[1]],
        landmark_ideas=[LANDMARK_OPTIONS[1]],
        portal_form=PORTAL_OPTIONS[0],
        theme_color_hexes=[
            THEME_COLORS["Strawberry Pink"],
            THEME_COLORS["Mint"],
            THEME_COLORS["Lavender"],
        ],
        playable=True,
    )


def _ensure_state() -> None:
    if "world_creation_mode" not in st.session_state:
        st.session_state.world_creation_mode = "prompt"
    if "world_draft" not in st.session_state or st.session_state.world_draft is None:
        st.session_state.world_draft = _default_profile()
    if "world_concept_candidates" not in st.session_state:
        st.session_state.world_concept_candidates = []
    if "editing_world_id" not in st.session_state:
        st.session_state.editing_world_id = None


def _reset_world() -> None:
    st.session_state.world_draft = _default_profile()
    st.session_state.world_source = ""
    st.session_state.world_concept_candidates = []
    st.session_state.editing_world_id = None


def _safe_index(options: list[str], value: str) -> int:
    try:
        return options.index(value)
    except ValueError:
        return 0


def render_world_factory(ctx, *, style_asset_id: str | None) -> None:
    _ensure_state()
    draft: WorldProfile = st.session_state.world_draft

    st.markdown("## 🌍 World Factory")
    st.caption("Imagine → Visualize → Choose → Blueprint → Build → Explore → Record")

    mode = st.radio(
        "How do you want to begin? / 想怎么开始？",
        ["✨ Prompt Generate / 描述生成", "🎨 Custom Build / 自定义搭建"],
        horizontal=True,
        index=0 if st.session_state.world_creation_mode == "prompt" else 1,
    )
    st.session_state.world_creation_mode = "prompt" if mode.startswith("✨") else "custom"

    name = st.text_input(
        "World Name / 世界名字",
        value=draft.world_name,
        placeholder="例如：Candy Cloud Valley",
        key="world_name_input",
    )

    source = st.text_area(
        "Imagine it / 描述你脑海里的世界",
        value=st.session_state.get("world_source", draft.source_description),
        placeholder=(
            "例如：一个只有晚上才会出现的云朵村，房子睡着以后屋顶会长出星星，"
            "桥下面有会发光的鲸鱼……"
        ),
        height=120,
        disabled=st.session_state.world_creation_mode != "prompt",
    )
    st.session_state.world_source = source

    st.markdown("### 1. Shape the World / 给世界定一个大方向")
    c1, c2, c3 = st.columns(3)
    with c1:
        world_type = st.selectbox(
            "World Type / 世界类型",
            WORLD_TYPE_OPTIONS,
            index=_safe_index(WORLD_TYPE_OPTIONS, draft.world_type),
        )
        season = st.selectbox(
            "Season / 季节",
            SEASON_OPTIONS,
            index=_safe_index(SEASON_OPTIONS, draft.season),
        )
        time_of_day = st.selectbox(
            "Time / 时间",
            TIME_OPTIONS,
            index=_safe_index(TIME_OPTIONS, draft.time_of_day),
        )
    with c2:
        reality_mode = st.selectbox(
            "Reality / 世界属性",
            REALITY_MODE_OPTIONS,
            index=_safe_index(REALITY_MODE_OPTIONS, draft.reality_mode),
        )
        weather = st.selectbox(
            "Weather / 天气",
            WEATHER_OPTIONS,
            index=_safe_index(WEATHER_OPTIONS, draft.weather),
        )
        terrain = st.multiselect(
            "Terrain / 地形",
            TERRAIN_OPTIONS,
            default=[x for x in draft.terrain if x in TERRAIN_OPTIONS] or [TERRAIN_OPTIONS[0]],
            max_selections=4,
        )
    with c3:
        mood = st.multiselect(
            "Mood / 氛围",
            MOOD_OPTIONS,
            default=[x for x in draft.mood if x in MOOD_OPTIONS] or [MOOD_OPTIONS[1]],
            max_selections=3,
        )
        landmarks = st.multiselect(
            "Landmarks / 地标",
            LANDMARK_OPTIONS,
            default=[x for x in draft.landmark_ideas if x in LANDMARK_OPTIONS] or [LANDMARK_OPTIONS[1]],
            max_selections=4,
        )
        portal = st.selectbox(
            "Portal / 传送门",
            PORTAL_OPTIONS,
            index=_safe_index(PORTAL_OPTIONS, draft.portal_form),
        )

    color_names = st.multiselect(
        "Theme Colors / 世界主题色",
        list(THEME_COLORS),
        default=[
            name
            for name, hex_value in THEME_COLORS.items()
            if hex_value in draft.theme_color_hexes
        ] or ["Strawberry Pink", "Mint", "Lavender"],
        max_selections=5,
    )
    color_hexes = [THEME_COLORS[x] for x in color_names]
    if color_hexes:
        swatches = "".join(
            f'<span class="mu-color-dot" style="background:{value}" title="{value}"></span>'
            for value in color_hexes
        )
        st.markdown(
            f'<div class="mu-color-row">{swatches}</div>',
            unsafe_allow_html=True,
        )

    extra = st.text_area(
        "Extra Details / 额外补充",
        value=draft.creator_extra_details,
        placeholder="Custom 选项、奇怪的小细节、必须出现的惊喜，都放这里。",
        height=90,
    )

    profile = WorldProfile(
        source_description=source,
        creator_extra_details=extra,
        world_name=name,
        world_type=world_type,
        reality_mode=reality_mode,
        terrain=terrain,
        season=season,
        weather=weather,
        time_of_day=time_of_day,
        mood=mood,
        landmark_ideas=landmarks,
        portal_form=portal,
        portal_placement_idea="Place the Portal where it creates a memorable reveal.",
        traversability_notes="Keep clear walkable routes connecting spawn, landmark and Portal.",
        theme_color_hexes=color_hexes,
        playable=True,
    )
    st.session_state.world_draft = profile

    st.markdown("### 2. Visualize / 先把梦想画出来")
    concept_count = st.segmented_control(
        "How many directions? / 生成几个方向？",
        options=[1, 2, 3],
        default=3,
        help="1 = Playable, 2 = Playable + Dream, 3 = Playable + Dream + Story",
    )
    concept_count = int(concept_count or 3)

    count = int(st.session_state.get("creator_generation_count", 0))
    remaining = max(0, MAX_GENERATIONS_PER_SESSION - count)
    st.caption(f"🎟️ 本次会话剩余生成次数：{remaining}/{MAX_GENERATIONS_PER_SESSION}")

    directions = ["playable", "dream", "story"][:concept_count]
    can_generate = bool(name) and ctx.world_concepts.is_available and remaining >= concept_count

    if st.button(
        "✨ Generate World Concepts / 生成世界概念图",
        type="primary",
        disabled=not can_generate,
        use_container_width=True,
    ):
        if not style_asset_id:
            st.error("Mini Utopia Global Style Canon 尚未连接。")
        else:
            try:
                editing_id = st.session_state.get("editing_world_id")
                if editing_id:
                    asset = ctx.assets.update_world(
                        asset_id=editing_id,
                        name=name,
                        description=source,
                        profile=profile,
                    )
                else:
                    asset = ctx.assets.create_world(
                        name=name,
                        description=source,
                        profile=profile,
                    )
                    st.session_state.editing_world_id = asset.asset_id

                generated = []
                with st.spinner("🌈 正在把你的世界想象画出来…"):
                    for direction in directions:
                        candidate = ctx.world_concepts.generate_candidate(
                            location_asset_id=asset.asset_id,
                            style_asset_id=style_asset_id,
                            direction=direction,
                        )
                        generated.append(
                            {"direction": direction, "path": candidate.path}
                        )

                st.session_state.world_concept_candidates = generated
                st.session_state.creator_generation_count = count + len(generated)
                st.rerun()
            except Exception as exc:
                st.error(f"World concept generation failed / 生成失败: {exc}")

    if not ctx.world_concepts.is_available:
        st.info("Image API 尚未连接；目前可以设计 World Profile，但不能生成 Concept Art。")

    candidates = st.session_state.get("world_concept_candidates", [])
    if candidates:
        st.markdown("### 3. Choose / 哪一个最像你脑海里的世界？")
        cols = st.columns(len(candidates))
        for col, candidate in zip(cols, candidates):
            with col:
                direction = candidate["direction"]
                try:
                    st.image(
                        ctx.storage.get_bytes(candidate["path"]),
                        caption=DIRECTION_LABELS.get(direction, direction),
                        use_container_width=True,
                    )
                except Exception:
                    st.warning("Concept image 暂时无法读取。")

                if st.button(
                    "💖 Choose This World / 就要这个",
                    key=f"choose_world_{direction}_{candidate['path']}",
                    use_container_width=True,
                ):
                    try:
                        asset_id = st.session_state.get("editing_world_id")
                        if not asset_id or not style_asset_id:
                            raise RuntimeError("World or Style asset is missing.")
                        ctx.world_concepts.approve_candidate(
                            location_asset_id=asset_id,
                            candidate_path=candidate["path"],
                            style_asset_id=style_asset_id,
                        )
                        st.session_state.world_concept_candidates = []
                        st.session_state.pending_app_page = "🗺️ My Worlds"
                        st.success("世界概念已锁定！下一步会把它变成可玩的 Blueprint。")
                        st.balloons()
                        st.rerun()
                    except Exception as exc:
                        st.error(f"World approval failed / 保存失败: {exc}")

        st.caption(
            "Concept Art 是视觉锚点，不是最终 3D 几何。"
            "下一阶段会把选中的方向转成 50×50 可扩展 World Blueprint。"
        )

    st.divider()
    if st.button("🆕 Start a New World / 新世界"):
        _reset_world()
        st.rerun()
