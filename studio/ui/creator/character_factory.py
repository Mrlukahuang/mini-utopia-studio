from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from studio.core.enums import AssetType
from studio.models.character import CharacterProfile, WearableLoadout
from studio.models.reference import ReferenceCharacterConfig
from studio.ui.creator.character_presets import (
    CUSTOM,
    AGE_OPTIONS,
    BODY_BUILD_OPTIONS,
    CHARACTER_TYPE_OPTIONS,
    COLOR_PRESETS,
    DISTINCTIVE_OPTIONS,
    EYE_SHAPE_OPTIONS,
    FACE_STYLE_OPTIONS,
    FAVORITE_COLOR_HEX,
    FAVORITE_COLOR_OPTIONS,
    HAIR_FUR_KIND_OPTIONS,
    HAIR_FUR_TEXTURE_OPTIONS,
    HAIRSTYLE_OPTIONS,
    HEIGHT_OPTIONS,
    LANGUAGE_OPTIONS,
    PERSONALITY_OPTIONS,
    SPEAKING_TONE_OPTIONS,
    STORY_ROLE_OPTIONS,
    STRENGTH_OPTIONS,
    WEAKNESS_OPTIONS,
)
from studio.ui.theme import render_game_hero, render_quest


DEFAULT_FAVORITE_COLOR_HEXES = ["#F7B7D2", "#B9E7D0", "#D7C2F3"]
MAX_GENERATIONS_PER_SESSION = 20

ENGLISH_LEVELS = {
    1: "几乎不会英语 / Almost no English",
    2: "会一些单词 / Isolated words",
    3: "会简单短语 / Simple phrases",
    4: "基础日常句子 / Basic everyday sentences",
    5: "可以简单对话 / Simple conversation",
    6: "日常交流比较自然 / Comfortable everyday English",
    7: "对话能力很好 / Good conversational English",
    8: "流利 / Fluent",
    9: "接近母语 / Near-native",
    10: "母语水平 / Native",
}


def english_level_label(level: int) -> str:
    return ENGLISH_LEVELS[level]


def relative_height_label(
    height_cm: float,
    anchor_names: list[str],
    anchor_heights: list[float],
) -> str:
    paired = sorted(zip(anchor_heights, anchor_names))
    (shorter_h, shorter_name), (taller_h, taller_name) = paired

    if height_cm < shorter_h * 0.75:
        return f"比 {shorter_name} 矮很多 / Much shorter than {shorter_name}"
    if height_cm < shorter_h * 0.95:
        return f"比 {shorter_name} 矮 / Shorter than {shorter_name}"
    if height_cm <= shorter_h * 1.05:
        return f"和 {shorter_name} 差不多高 / Around {shorter_name}"
    if height_cm < taller_h * 0.95:
        return (
            f"在 {shorter_name} 和 {taller_name} 之间 / "
            f"Between {shorter_name} and {taller_name}"
        )
    if height_cm <= taller_h * 1.05:
        return f"和 {taller_name} 差不多高 / Around {taller_name}"
    if height_cm < taller_h * 1.35:
        return f"比 {taller_name} 高 / Taller than {taller_name}"
    return f"比 {taller_name} 高很多 / Much taller than {taller_name}"


def _position(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 50.0
    return max(0.0, min(100.0, (value - minimum) / (maximum - minimum) * 100))


def render_height_ruler(
    *,
    minimum: float,
    maximum: float,
    height_cm: float,
    anchor_names: list[str],
    anchor_heights: list[float],
) -> None:
    colors = ["#A8E6CF", "#CDB4FF"]
    markers = []
    for idx, (name, value) in enumerate(zip(anchor_names, anchor_heights)):
        pos = _position(value, minimum, maximum)
        markers.append(
            f"""
            <div class="mu-ruler-marker" style="left:{pos:.2f}%">
                <div class="mu-ruler-dot" style="background:{colors[idx]}"></div>
                <div class="mu-ruler-label">{escape(name)}<br><b>{value:.0f} cm</b></div>
            </div>
            """
        )

    current_pos = _position(height_cm, minimum, maximum)
    markers.append(
        f"""
        <div class="mu-ruler-marker mu-current" style="left:{current_pos:.2f}%">
            <div class="mu-ruler-dot" style="background:#FF9FB2"></div>
            <div class="mu-ruler-label">✨ New Character<br><b>{height_cm:.0f} cm</b></div>
        </div>
        """
    )

    st.markdown(
        f"""
        <div class="mu-ruler-wrap">
            <div class="mu-ruler-scale">
                <span>{minimum:.0f} cm</span>
                <span>{maximum:.0f} cm</span>
            </div>
            <div class="mu-ruler-track">{''.join(markers)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _preset_index(options: list[str], value: str, default: int = 0) -> int:
    if value in options:
        return options.index(value)
    if value and CUSTOM in options:
        return options.index(CUSTOM)
    return max(0, min(default, len(options) - 1))


def _choice(selected: str, previous: str, options: list[str]) -> str:
    if selected != CUSTOM:
        return selected
    if previous and previous not in options:
        return previous
    return CUSTOM


def _color_name(hex_value: str, text_value: str) -> str:
    for name, value in COLOR_PRESETS.items():
        if value and value.lower() == (hex_value or "").lower():
            return name
    if text_value in COLOR_PRESETS:
        return text_value
    return CUSTOM


def _wearables_for_slot(assets: list[Any], slot: str) -> list[Any]:
    return [
        asset
        for asset in assets
        if not asset.metadata.get("wearable_type")
        or asset.metadata.get("wearable_type") == slot
    ]


def _asset_selector(label: str, assets: list[Any], current_id: str | None, key: str):
    options = [None, *assets]
    index = 0
    for idx, asset in enumerate(options):
        if asset is not None and asset.asset_id == current_id:
            index = idx
            break
    return st.selectbox(
        label,
        options,
        index=index,
        format_func=lambda item: "— 未选择 / None —" if item is None else item.display_name,
        key=key,
    )


def render_reference_settings(ctx) -> None:
    with st.expander("📏 Reference Anchors / 参考角色设置", expanded=False):
        st.caption(
            "参考角色本身仍然是普通 Character Asset。这里只保存两个 CHAR_ID，"
            "不会复制名字或身高数据。"
        )
        eligible = ctx.references.eligible_characters()
        current = ctx.references.load()
        current_ids = current.character_asset_ids if current else []
        defaults = [a for a in eligible if a.asset_id in current_ids]

        if len(eligible) < 2:
            st.info("至少需要两个已经填写精确身高的角色，才能设置 Reference Anchors。")
            return

        selected = st.multiselect(
            "选择两个参考角色 / Choose two reference characters",
            eligible,
            default=defaults,
            max_selections=2,
            format_func=lambda asset: (
                f"{asset.display_name} · "
                f"{asset.metadata.get('character_profile', {}).get('height_cm', '?')} cm"
            ),
            key="reference_anchor_selector",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "💾 Save Reference Anchors / 保存参考角色",
                disabled=len(selected) != 2,
                use_container_width=True,
            ):
                ctx.references.save(
                    ReferenceCharacterConfig(
                        character_asset_ids=[a.asset_id for a in selected]
                    )
                )
                st.success("Reference Anchors 已保存。")
        with c2:
            if current and st.button("清除 / Clear", use_container_width=True):
                ctx.references.clear()
                st.rerun()


def _start_over() -> None:
    for key in (
        "char_draft",
        "char_source",
        "char_name",
        "character_name_input",
        "char_creation_mode",
        "char_stage",
        "editing_character_id",
        "character_master_candidate_path",
        "character_master_character_id",
    ):
        st.session_state.pop(key, None)
    st.rerun()


def render_character_factory(ctx, character_factory, *, studio_mode: bool = False) -> None:
    """Character Factory v1 final: two entry modes, preset-first Custom Build."""

    render_game_hero(
        "Create Your Mini Hero ✨",
        "两种方式开始，同一套 Mini Utopia 规则完成。选项负责稳定，想象力留在最后的 Extra Details。",
        kicker="CHARACTER FACTORY · FINAL V1",
    )

    if studio_mode:
        render_reference_settings(ctx)

    draft: CharacterProfile | None = st.session_state.get("char_draft")
    mode = st.session_state.get("char_creation_mode")

    if draft is None and mode is None:
        render_quest("你想怎么开始？ / How do you want to start?")
        left, right = st.columns(2)

        with left:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">✨📝</div>'
                '<h3>Prompt Generate</h3>'
                '<p>描述生成 · 用一句话说出脑海里的角色，系统先整理，再让你确认。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "✨ Prompt Generate / 描述生成",
                key="start_prompt_generate",
                use_container_width=True,
            ):
                st.session_state.char_creation_mode = "prompt"
                st.rerun()

        with right:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">🎨🧩</div>'
                '<h3>Custom Build</h3>'
                '<p>自定义搭建 · 像游戏捏人一样，从预设选项一步步搭出来。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "🎨 Custom Build / 自定义搭建",
                key="start_custom_build",
                use_container_width=True,
            ):
                st.session_state.char_creation_mode = "custom"
                st.session_state.char_draft = CharacterProfile()
                st.session_state.char_stage = 0
                st.rerun()
        return

    if draft is None and mode == "prompt":
        render_quest("把脑海里的角色讲出来。下一步会自动变成同一套可编辑选项。")
        description = st.text_area(
            "描述 TA / Describe your character",
            value=st.session_state.get("char_source", ""),
            placeholder=(
                "例如：一个8岁的女孩，长卷棕发，大大的焦糖色眼睛，"
                "喜欢星星，有点害羞但很爱冒险。"
            ),
            height=150,
            key="character_source_text",
        )
        a, b = st.columns([2, 1])
        with a:
            if st.button(
                "✨ Build My Character / 帮我整理",
                type="primary",
                disabled=not description.strip(),
                use_container_width=True,
            ):
                st.session_state.char_source = description
                st.session_state.char_draft = character_factory.parse_description(description)
                st.session_state.char_creation_mode = "custom"
                st.session_state.char_stage = 0
                st.rerun()
        with b:
            if st.button("← Back / 返回", use_container_width=True):
                st.session_state.char_creation_mode = None
                st.rerun()
        return

    draft = st.session_state.get("char_draft")
    if draft is None:
        return

    stages = [
        "1 · Identity / 身份",
        "2 · Look / 外形",
        "3 · Personality / 性格",
        "4 · Outfit & Details / 装备",
        "5 · Create / 生成",
    ]
    stage = max(0, min(int(st.session_state.get("char_stage", 0)), 4))
    st.progress((stage + 1) / 5, text=f"{stages[stage]} · {stage + 1}/5")
    st.caption("Custom Build 以选择题为主。只有最后的 Extra Details 是自由描述。")

    def go(value: int) -> None:
        st.session_state.char_stage = max(0, min(value, 4))
        st.rerun()

    if stage == 0:
        st.markdown("### 👤 Identity / TA 是谁？")
        a, b = st.columns(2)
        with a:
            name = st.text_input(
                "名字 / Name",
                value=st.session_state.get("char_name", ""),
                placeholder="给 TA 取一个名字",
                key="character_name_input",
            )
            ctype = st.selectbox(
                "Character Type / 角色类型",
                CHARACTER_TYPE_OPTIONS,
                index=_preset_index(CHARACTER_TYPE_OPTIONS, draft.character_type),
            )
            age = st.selectbox(
                "Age / 年龄",
                AGE_OPTIONS,
                index=_preset_index(AGE_OPTIONS, draft.age, default=4),
            )
        with b:
            role = st.selectbox(
                "Story Role / 故事角色",
                STORY_ROLE_OPTIONS,
                index=_preset_index(STORY_ROLE_OPTIONS, draft.story_role),
            )
            build = st.selectbox(
                "Body Build / 体型",
                BODY_BUILD_OPTIONS,
                index=_preset_index(BODY_BUILD_OPTIONS, draft.body_build, default=2),
            )
            face = st.selectbox(
                "Face Style / 脸部感觉",
                FACE_STYLE_OPTIONS,
                index=_preset_index(FACE_STYLE_OPTIONS, draft.face),
            )

        if draft.source_description:
            st.info("✨ Prompt 已整理成选项。你可以继续修改；原始描述会保留在 Profile。")

        if st.button("Next → Look", type="primary", use_container_width=True):
            st.session_state.char_name = name
            st.session_state.char_draft = draft.model_copy(
                update={
                    "character_type": _choice(ctype, draft.character_type, CHARACTER_TYPE_OPTIONS),
                    "age": _choice(age, draft.age, AGE_OPTIONS),
                    "story_role": _choice(role, draft.story_role, STORY_ROLE_OPTIONS),
                    "body_build": _choice(build, draft.body_build, BODY_BUILD_OPTIONS),
                    "face": _choice(face, draft.face, FACE_STYLE_OPTIONS),
                }
            )
            go(1)
        return

    if stage == 1:
        st.markdown("### 🎨 Look / TA 长什么样？")
        a, b = st.columns(2)
        with a:
            hair_kind = st.selectbox(
                "Hair or Fur / 头发或毛发",
                HAIR_FUR_KIND_OPTIONS,
                index=_preset_index(HAIR_FUR_KIND_OPTIONS, draft.hair_or_fur),
            )
            texture = st.selectbox(
                "Texture / 质感",
                HAIR_FUR_TEXTURE_OPTIONS,
                index=_preset_index(HAIR_FUR_TEXTURE_OPTIONS, draft.skin_fur_material),
            )
            hairstyle = st.selectbox(
                "Hairstyle / 发型",
                HAIRSTYLE_OPTIONS,
                index=_preset_index(HAIRSTYLE_OPTIONS, draft.hair_style),
            )
            hair_color = st.selectbox(
                "Hair / Fur Color / 头发毛发颜色",
                list(COLOR_PRESETS),
                index=list(COLOR_PRESETS).index(
                    _color_name(draft.hair_or_fur_color_hex, draft.hair_or_fur_color)
                ),
            )
        with b:
            eye_shape = st.selectbox(
                "Eye Shape / 眼睛形状",
                EYE_SHAPE_OPTIONS,
                index=_preset_index(EYE_SHAPE_OPTIONS, draft.eyes.shape),
            )
            eye_color = st.selectbox(
                "Eye Color / 眼睛颜色",
                list(COLOR_PRESETS),
                index=list(COLOR_PRESETS).index(
                    _color_name(draft.eyes.color_hex, draft.eyes.color)
                ),
            )
            favorite_colors = st.multiselect(
                "Favorite Colors / 最喜欢的颜色（最多 3 个）",
                FAVORITE_COLOR_OPTIONS,
                default=[
                    value for value in draft.favorite_colors
                    if value in FAVORITE_COLOR_OPTIONS
                ][:3],
                max_selections=3,
            )
            distinctive = st.selectbox(
                "Distinctive Feature / 特别特征",
                DISTINCTIVE_OPTIONS,
                index=_preset_index(
                    DISTINCTIVE_OPTIONS,
                    draft.distinctive_features[0]
                    if draft.distinctive_features else "",
                ),
            )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", key="look_back", use_container_width=True):
                go(0)
        with nxt:
            if st.button("Next → Personality", type="primary", use_container_width=True):
                hair_hex = COLOR_PRESETS.get(hair_color) or draft.hair_or_fur_color_hex
                eye_hex = COLOR_PRESETS.get(eye_color) or draft.eyes.color_hex
                fav_hexes = [
                    FAVORITE_COLOR_HEX[value]
                    for value in favorite_colors
                    if value in FAVORITE_COLOR_HEX
                ]
                st.session_state.char_draft = draft.model_copy(
                    update={
                        "hair_or_fur": _choice(
                            hair_kind, draft.hair_or_fur, HAIR_FUR_KIND_OPTIONS
                        ),
                        "skin_fur_material": _choice(
                            texture,
                            draft.skin_fur_material,
                            HAIR_FUR_TEXTURE_OPTIONS,
                        ),
                        "hair_style": _choice(
                            hairstyle, draft.hair_style, HAIRSTYLE_OPTIONS
                        ),
                        "hair_or_fur_color": hair_color,
                        "hair_or_fur_color_hex": hair_hex,
                        "eyes": draft.eyes.model_copy(
                            update={
                                "shape": _choice(
                                    eye_shape, draft.eyes.shape, EYE_SHAPE_OPTIONS
                                ),
                                "color": eye_color,
                                "color_hex": eye_hex,
                            }
                        ),
                        "favorite_colors": favorite_colors,
                        "favorite_color_hexes": (
                            fav_hexes or DEFAULT_FAVORITE_COLOR_HEXES
                        ),
                        "distinctive_features": (
                            [] if not distinctive else [distinctive]
                        ),
                        "appearance": (
                            draft.appearance
                            or "cute Mini Utopia playable avatar with clean block-built toy forms"
                        ),
                    }
                )
                go(2)
        return

    if stage == 2:
        st.markdown("### 💬 Personality / TA 是什么性格？")
        a, b = st.columns(2)
        with a:
            personality = st.multiselect(
                "Personality / 性格（最多 3 个）",
                PERSONALITY_OPTIONS,
                default=[
                    value for value in draft.personality_traits
                    if value in PERSONALITY_OPTIONS
                ][:3],
                max_selections=3,
            )
            strength = st.selectbox(
                "Strength / 擅长",
                STRENGTH_OPTIONS,
                index=_preset_index(
                    STRENGTH_OPTIONS,
                    draft.strengths[0] if draft.strengths else "",
                ),
            )
            weakness = st.selectbox(
                "Little Weakness / 小弱点",
                WEAKNESS_OPTIONS,
                index=_preset_index(
                    WEAKNESS_OPTIONS,
                    draft.weaknesses[0] if draft.weaknesses else "",
                ),
            )
        with b:
            tone = st.selectbox(
                "Speaking Tone / 说话语气",
                SPEAKING_TONE_OPTIONS,
                index=_preset_index(SPEAKING_TONE_OPTIONS, draft.speaking_tone),
            )
            language = st.selectbox(
                "Native Language / 母语",
                LANGUAGE_OPTIONS,
                index=_preset_index(LANGUAGE_OPTIONS, draft.native_language),
            )
            english = st.selectbox(
                "English Level / 英语水平",
                list(range(1, 11)),
                index=max(0, min((draft.english_level or 5) - 1, 9)),
                format_func=lambda level: f"{level} · {english_level_label(level)}",
            )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", key="personality_back", use_container_width=True):
                go(1)
        with nxt:
            if st.button("Next → Outfit", type="primary", use_container_width=True):
                st.session_state.char_draft = draft.model_copy(
                    update={
                        "personality_traits": personality,
                        "strengths": [] if not strength else [strength],
                        "weaknesses": [] if not weakness else [weakness],
                        "speaking_tone": _choice(
                            tone, draft.speaking_tone, SPEAKING_TONE_OPTIONS
                        ),
                        "native_language": _choice(
                            language, draft.native_language, LANGUAGE_OPTIONS
                        ),
                        "english_level": english,
                    }
                )
                go(3)
        return

    if stage == 3:
        st.markdown("### 👕📏 Outfit & Details / 穿什么、有多高？")
        height = st.selectbox(
            "Height Category / 身高感觉",
            HEIGHT_OPTIONS,
            index=_preset_index(HEIGHT_OPTIONS, draft.height, default=2),
        )

        resolved = ctx.references.resolved_anchors()
        if resolved:
            config, anchor_assets, anchor_heights = resolved
            minimum, maximum = config.height_bounds(anchor_heights)
            initial = float(draft.height_cm or sum(anchor_heights) / len(anchor_heights))
            initial = min(max(initial, minimum), maximum)
            height_cm = st.slider(
                "Exact Height / 精确身高",
                min_value=float(round(minimum, 1)),
                max_value=float(round(maximum, 1)),
                value=float(round(initial, 1)),
                step=1.0,
                format="%.0f cm",
            )
            render_height_ruler(
                minimum=minimum,
                maximum=maximum,
                height_cm=height_cm,
                anchor_names=[asset.display_name for asset in anchor_assets],
                anchor_heights=anchor_heights,
            )
        else:
            height_cm = st.number_input(
                "Exact Height / 精确身高 (cm)",
                min_value=1.0,
                max_value=1000.0,
                value=float(draft.height_cm or 120.0),
                step=1.0,
            )

        defaults = ctx.assets.ensure_default_character_wearables()
        wear_assets = ctx.repository.list_assets(AssetType.WEARABLE)
        c1, c2 = st.columns(2)
        with c1:
            top = _asset_selector(
                "Top / 上衣",
                _wearables_for_slot(wear_assets, "top"),
                draft.wearables.top_id or defaults["top"].asset_id,
                "wear_top",
            )
            bottom = _asset_selector(
                "Bottom / 下装",
                _wearables_for_slot(wear_assets, "bottom"),
                draft.wearables.bottom_id or defaults["bottom"].asset_id,
                "wear_bottom",
            )
        with c2:
            shoes = _asset_selector(
                "Shoes / 鞋子",
                _wearables_for_slot(wear_assets, "shoes"),
                draft.wearables.shoes_id,
                "wear_shoes",
            )
            hat = _asset_selector(
                "Hat / 帽子",
                _wearables_for_slot(wear_assets, "hat"),
                draft.wearables.hat_id,
                "wear_hat",
            )

        prop_assets = ctx.repository.list_assets(AssetType.PROP)
        selected_props = st.multiselect(
            "Starting Props / 初始道具（最多 2 个）",
            prop_assets,
            default=[
                prop for prop in prop_assets
                if prop.asset_id in draft.starting_prop_ids
            ],
            format_func=lambda asset: asset.display_name,
            max_selections=2,
        )

        st.divider()
        extra = st.text_area(
            "✨ Extra Details / 额外补充",
            value=draft.creator_extra_details,
            placeholder=(
                "只有这里自由发挥：TA 来自哪里？有什么特殊能力？"
                "如果上面某项选了 Custom，也在这里说明。"
            ),
            height=120,
            help="Custom Build 唯一的自由描述区。",
        )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", key="outfit_back", use_container_width=True):
                go(2)
        with nxt:
            if st.button("Next → Create", type="primary", use_container_width=True):
                st.session_state.char_draft = draft.model_copy(
                    update={
                        "height": _choice(height, draft.height, HEIGHT_OPTIONS),
                        "height_cm": height_cm,
                        "creator_extra_details": extra,
                        "wearables": WearableLoadout(
                            top_id=top.asset_id if top else None,
                            bottom_id=bottom.asset_id if bottom else None,
                            shoes_id=shoes.asset_id if shoes else None,
                            hat_id=hat.asset_id if hat else None,
                            accessory_ids=draft.wearables.accessory_ids,
                        ),
                        "starting_prop_ids": [
                            prop.asset_id for prop in selected_props
                        ],
                    }
                )
                go(4)
        return

    final_profile = draft
    name = st.session_state.get("char_name", "").strip()
    missing = final_profile.missing_core_fields()

    st.markdown("### ✨ Create / 生成角色设定图")
    info, palette_col = st.columns([1.4, 1])
    with info:
        st.markdown(f"#### {escape(name) if name else 'New Character'}")
        st.write(f"**Type** · {final_profile.character_type or '—'}")
        st.write(f"**Role** · {final_profile.story_role or '—'}")
        st.write(f"**Height** · {final_profile.height_cm or '—'} cm")
        st.write(
            "**Personality** · "
            + (" · ".join(final_profile.personality_traits) or "—")
        )
        if final_profile.creator_extra_details:
            st.caption("Extra · " + final_profile.creator_extra_details)
    with palette_col:
        st.markdown("#### 🎨 Canon Colors")
        colors = final_profile.favorite_color_hexes or DEFAULT_FAVORITE_COLOR_HEXES
        swatches = "".join(
            (
                '<span style="display:inline-block;width:34px;height:34px;'
                f'border-radius:12px;background:{color};margin:4px;'
                'border:1px solid rgba(0,0,0,.08)"></span>'
            )
            for color in colors[:3]
        )
        st.markdown(swatches, unsafe_allow_html=True)
        st.caption(
            f"Hair/Fur {final_profile.hair_or_fur_color_hex} · "
            f"Eyes {final_profile.eyes.color_hex}"
        )
        st.caption("🔒 Mini Playable Avatar · 2.8–3.0 heads tall")

    if missing:
        st.warning("还差这些核心设定：" + ", ".join(missing))
    if not name:
        st.warning("请返回 Identity 给 TA 取一个名字。")

    count = int(st.session_state.get("creator_generation_count", 0))
    remaining = max(0, MAX_GENERATIONS_PER_SESSION - count)
    st.caption(f"🎟️ 本次会话剩余生成次数：{remaining}/{MAX_GENERATIONS_PER_SESSION}")

    candidate_path = st.session_state.get("character_master_candidate_path")
    back, generate = st.columns([1, 2])
    with back:
        if st.button("← Back to Edit", use_container_width=True):
            go(3)
    with generate:
        if st.button(
            (
                "✨ Generate Master Sheet / 生成角色设定图"
                if not candidate_path
                else "🎲 Regenerate / 再生成"
            ),
            type="primary",
            disabled=(
                bool(missing)
                or not name
                or not ctx.character_masters.is_available
                or remaining <= 0
            ),
            use_container_width=True,
        ):
            try:
                editing_id = st.session_state.get("editing_character_id")
                asset = character_factory.save_character(
                    name=name,
                    description=st.session_state.get("char_source", ""),
                    profile=final_profile,
                    asset_id=editing_id,
                )
                st.session_state.editing_character_id = asset.asset_id
                style_asset = ctx.styles.ensure_mini_utopia_base()
                with st.spinner("✨ 正在生成 Hero + Turnaround + Expressions…"):
                    candidate = ctx.character_masters.generate_candidate(
                        character_asset_id=asset.asset_id,
                        style_asset_id=style_asset.asset_id,
                    )
                st.session_state.character_master_candidate_path = candidate.path
                st.session_state.character_master_character_id = asset.asset_id
                st.session_state.creator_generation_count = count + 1
                st.rerun()
            except Exception as exc:
                st.error(f"生成失败 / Generation failed: {exc}")

    candidate_path = st.session_state.get("character_master_candidate_path")
    candidate_character_id = st.session_state.get("character_master_character_id")
    if candidate_path and candidate_character_id:
        st.divider()
        st.markdown("### 🌟 Character Master Sheet")
        art, facts = st.columns([2.2, 1])
        with art:
            try:
                st.image(
                    ctx.storage.get_bytes(candidate_path),
                    caption=(
                        "Visual Master · Hero + Front + 3/4 + Side + Back + Expressions"
                    ),
                    use_container_width=True,
                )
            except Exception:
                st.warning("图片暂时无法读取，可以点击 Regenerate。")
        with facts:
            st.markdown("#### 📋 Canon Profile")
            st.write(f"**Name** · {name}")
            st.write(f"**Type** · {final_profile.character_type}")
            st.write(f"**Age** · {final_profile.age}")
            st.write(f"**Role** · {final_profile.story_role or '—'}")
            st.write(
                f"**Height** · {final_profile.height_cm:.0f} cm"
                if final_profile.height_cm else
                "**Height** · —"
            )
            st.caption("所有文字和数据由系统渲染，不允许图片模型自己编写。")

        keep, new = st.columns([2, 1])
        with keep:
            if st.button(
                "💖 Keep This Look / 就要这个！",
                type="primary",
                use_container_width=True,
            ):
                try:
                    ctx.character_masters.approve_candidate(
                        character_asset_id=candidate_character_id,
                        candidate_path=candidate_path,
                    )
                    st.session_state.character_master_candidate_path = None
                    st.session_state.character_master_character_id = None
                    st.session_state.editing_character_id = None
                    st.session_state.pending_app_page = "🎭 My Characters"
                    st.success(
                        f"角色正式加入 Mini Utopia！ · {candidate_character_id}"
                    )
                    st.balloons()
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存失败 / Approval failed: {exc}")
        with new:
            if st.button("🆕 New Character / 新角色", use_container_width=True):
                _start_over()

    if not ctx.character_masters.is_available:
        st.info("Image API 尚未连接；当前只能保存 Character Profile。")
