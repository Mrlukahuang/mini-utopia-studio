from __future__ import annotations

from html import escape
import random
from typing import Any

import streamlit as st

from studio.core.enums import AssetType
from studio.models.character import (
    CharacterProfile,
    EyeProfile,
    WearableLoadout,
)
from studio.models.reference import ReferenceCharacterConfig
from studio.ui.theme import render_game_hero, render_quest


HAIRSTYLE_OPTIONS = [
    "",
    "长直发 / Long straight",
    "长卷发 / Long curly",
    "短发 / Short hair",
    "波波头 / Bob",
    "高马尾 / High ponytail",
    "低马尾 / Low ponytail",
    "双马尾 / Pigtails",
    "丸子头 / Bun",
    "双丸子头 / Double buns",
    "单辫 / Single braid",
    "双辫 / Twin braids",
    "法式辫 / French braid",
    "荷兰辫 / Dutch braid",
    "鱼骨辫 / Fishtail braid",
    "侧辫 / Side braid",
    "皇冠辫 / Crown braid",
    "半扎发 / Half-up",
    "精灵短发 / Pixie cut",
    "其他 / Other",
]

BODY_BUILD_OPTIONS = [
    "",
    "很瘦 / Very slim",
    "偏瘦 / Slim",
    "普通 / Average",
    "圆润 / Round",
    "胖胖的 / Chubby",
    "壮壮的 / Strong",
]

HEIGHT_OPTIONS = [
    "",
    "很矮 / Very short",
    "偏矮 / Short",
    "中等 / Medium",
    "偏高 / Tall",
    "很高 / Very tall",
]


CHARACTER_TYPE_OPTIONS = [
    "人类 / Human",
    "动物 / Animal",
    "机器人 / Robot",
    "奇幻生物 / Fantasy Creature",
    "精灵 / Spirit",
    "云朵生物 / Cloud Creature",
    "外星生物 / Alien",
    "玩具角色 / Toy Character",
    "植物生物 / Plant Creature",
    "交通工具角色 / Vehicle Character",
    "其他 / Other",
]

STORY_ROLE_OPTIONS = [
    "",
    "旅行者 / Traveler",
    "探险家 / Explorer",
    "发明家 / Inventor",
    "守护者 / Guardian",
    "伙伴 / Friend",
    "向导 / Guide",
    "收藏家 / Collector",
    "梦想家 / Dreamer",
    "科学家 / Scientist",
    "艺术家 / Artist",
    "信使 / Messenger",
    "神秘角色 / Mystery Role",
    "其他 / Other",
]

DEFAULT_FAVORITE_COLOR_HEXES = ["#F7B7D2", "#B9E7D0", "#D7C2F3"]
MAX_GENERATIONS_PER_SESSION = 20

SURPRISE_TEMPLATES = [
    CharacterProfile(
        character_type="动物 / Animal",
        character_type_description="一只圆滚滚、喜欢收集发光石头的小熊猫",
        age="7",
        appearance="small round explorer with a huge friendly head",
        hair_or_fur="soft fluffy fur",
        hair_or_fur_color="cream white and soft charcoal",
        hair_or_fur_color_hex="#F2EBDD",
        body_build="圆润 / Round",
        height="偏矮 / Short",
        height_cm=105,
        favorite_colors=["薄荷绿", "杏桃色", "天空蓝"],
        favorite_color_hexes=["#B9E7D0", "#F6C69A", "#BDE3F5"],
        personality_traits=["好奇", "谨慎", "幽默"],
        speaking_tone="轻快、可爱",
        native_language="中文",
        english_level=5,
        story_role="探险家 / Explorer",
    ),
    CharacterProfile(
        character_type="机器人 / Robot",
        character_type_description="会在开心时投影小蝴蝶的圆角小机器人",
        age="10",
        appearance="compact friendly modular robot with a large expressive face screen",
        hair_or_fur="soft toy-like shell",
        hair_or_fur_color="cream white",
        hair_or_fur_color_hex="#F6F1E8",
        body_build="普通 / Average",
        height="偏矮 / Short",
        height_cm=90,
        favorite_colors=["婴儿蓝", "薰衣草紫", "开心果绿"],
        favorite_color_hexes=["#BFDFF5", "#D7C2F3", "#C8E4B2"],
        personality_traits=["聪明", "热情", "有点健忘"],
        speaking_tone="兴奋、直接",
        native_language="中文",
        english_level=6,
        story_role="发明家 / Inventor",
    ),
    CharacterProfile(
        character_type="奇幻生物 / Fantasy Creature",
        character_type_description="一只会感应 Portal 的小星光龙",
        age="6",
        appearance="tiny gentle dragon with rounded wings and a very large cute head",
        hair_or_fur="soft rounded scales",
        hair_or_fur_color="lavender",
        hair_or_fur_color_hex="#CDB4E8",
        body_build="普通 / Average",
        height="中等 / Medium",
        height_cm=112,
        favorite_colors=["薰衣草紫", "薄荷绿", "柔和珊瑚"],
        favorite_color_hexes=["#D7C2F3", "#B9E7D0", "#F3B3A7"],
        personality_traits=["忠诚", "温柔", "爱玩"],
        speaking_tone="温柔、慢慢的",
        native_language="中文",
        english_level=4,
        story_role="守护者 / Guardian",
    ),
]

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


def split_items(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.replace("，", ",").split(",")
        if item.strip()
    ]


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
            <div class="mu-ruler-track">
                {''.join(markers)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _select_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _guided_index(options: list[str], value: str) -> int:
    if value in options:
        return options.index(value)
    if value and "其他 / Other" in options:
        return options.index("其他 / Other")
    return 0


def _wearables_for_slot(assets: list[Any], slot: str) -> list[Any]:
    """Keep typed default wearables out of unrelated slots.

    Legacy/user-created wearables without a subtype remain available everywhere
    until the dedicated Wearable Factory adds stricter categories.
    """
    return [
        asset
        for asset in assets
        if not asset.metadata.get("wearable_type")
        or asset.metadata.get("wearable_type") == slot
    ]


def _asset_selector(label: str, assets: list[Any], current_id: str | None, key: str):
    default_index = 0
    options = [None, *assets]
    if current_id:
        for idx, asset in enumerate(options):
            if asset is not None and asset.asset_id == current_id:
                default_index = idx
                break
    return st.selectbox(
        label,
        options,
        index=default_index,
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
            st.info(
                "至少需要两个已经填写精确身高的角色，才能设置 Reference Anchors。"
                "可以先创建角色，再回来设置。"
            )
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

        c1, c2 = st.columns([1, 1])
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
            if current and st.button(
                "清除 / Clear",
                use_container_width=True,
            ):
                ctx.references.clear()
                st.success("Reference Anchors 已清除。")
                st.rerun()


def render_character_factory(ctx, character_factory, *, studio_mode: bool = False) -> None:
    """Child-facing Character Factory v1.

    The creator sees one decision group at a time. Production complexity stays
    behind the structured Character Profile and Studio tools.
    """
    render_game_hero(
        "Create Your Mini Hero ✨",
        "像游戏捏人一样，一步一步创造 TA。你决定角色是谁，Mini Utopia "
        "负责让 TA 属于同一个世界。",
        kicker="CHARACTER FACTORY · CREATE A HERO",
    )

    if studio_mode:
        render_reference_settings(ctx)

    draft: CharacterProfile | None = st.session_state.get("char_draft")
    creation_mode = st.session_state.get("char_creation_mode")

    # ------------------------------------------------------------------
    # Start screen — exactly three ways to begin.
    # ------------------------------------------------------------------
    if draft is None and creation_mode is None:
        render_quest("你想怎么开始？ / How do you want to start?")
        a, b, c = st.columns(3)

        with a:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">✨📝</div>'
                '<h3>Describe & Create</h3><p>描述生成 · 把脑子里的角色讲出来，系统帮你整理。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button("✨ 描述生成", key="start_describe", use_container_width=True):
                st.session_state.char_creation_mode = "describe"
                st.rerun()

        with b:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">🎨🧸</div>'
                '<h3>Design My Own</h3><p>我来设计 · 从类型、眼睛、头发、衣服一步一步捏。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button("🎨 我来设计", key="start_design", use_container_width=True):
                st.session_state.char_creation_mode = "design"
                st.session_state.char_draft = CharacterProfile()
                st.session_state.char_stage = 0
                st.rerun()

        with c:
            st.markdown(
                '<div class="mu-world-card"><div class="emoji">🎲🌈</div>'
                '<h3>Surprise Me</h3><p>随机一个 · 先得到一个惊喜角色，再把 TA 改成自己的。</p></div>',
                unsafe_allow_html=True,
            )
            if st.button("🎲 随机一个", key="start_surprise", use_container_width=True):
                st.session_state.char_creation_mode = "surprise"
                st.session_state.char_draft = random.choice(SURPRISE_TEMPLATES).model_copy(deep=True)
                st.session_state.char_name = ""
                st.session_state.char_stage = 0
                st.rerun()
        return

    if draft is None and creation_mode == "describe":
        render_quest("像讲故事一样说一句就够了，后面每个细节都还能改。")
        description = st.text_area(
            "描述 TA / Describe your character",
            value=st.session_state.get("char_source", ""),
            placeholder=(
                "例如：一只胖胖的大熊猫，喜欢收集星星，有点胆小，"
                "但每次看到新的 Portal 都忍不住想进去。"
            ),
            height=150,
            key="character_source_text",
        )
        c1, c2 = st.columns([2, 1])
        with c1:
            if st.button(
                "✨ Turn This Into a Character / 帮我变成角色",
                type="primary",
                disabled=not description.strip(),
                use_container_width=True,
            ):
                st.session_state.char_source = description
                st.session_state.char_draft = character_factory.parse_description(description)
                st.session_state.char_name = ""
                st.session_state.char_stage = 0
                st.rerun()
        with c2:
            if st.button("← 换一种开始方式", use_container_width=True):
                st.session_state.char_creation_mode = None
                st.rerun()
        return

    draft = st.session_state.get("char_draft")
    if draft is None:
        return

    stages = [
        "1 · Who / TA是谁",
        "2 · Look / 长什么样",
        "3 · Personality / 性格",
        "4 · Outfit & Size / 穿什么多高",
        "5 · Create / 生成",
    ]
    stage = int(st.session_state.get("char_stage", 0))
    stage = max(0, min(stage, len(stages) - 1))

    st.progress((stage + 1) / len(stages), text=f"{stages[stage]}  ·  {stage + 1}/5")
    st.caption("一次只做几件事。随时可以返回修改，角色的永久 CHAR_ID 不会因为编辑而改变。")

    def go(next_stage: int) -> None:
        st.session_state.char_stage = max(0, min(next_stage, 4))
        st.rerun()

    # ------------------------------------------------------------------
    # Stage 1: identity
    # ------------------------------------------------------------------
    if stage == 0:
        st.markdown("### 👤 TA 是谁？")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input(
                "名字 / Name",
                value=st.session_state.get("char_name", ""),
                placeholder="给 TA 取一个名字",
                key="character_name_input",
            )
            character_type = st.selectbox(
                "TA是什么？ / Character Type",
                CHARACTER_TYPE_OPTIONS,
                index=_guided_index(CHARACTER_TYPE_OPTIONS, draft.character_type),
            )
            type_detail = st.text_area(
                "这个类型有什么特别？ / Type Detail",
                value=draft.character_type_description,
                placeholder="例如：一只会收集星星的圆滚滚熊猫",
                height=90,
            )
        with c2:
            age = st.text_input("年龄 / Age", value=draft.age, placeholder="例如：8")
            story_role = st.selectbox(
                "故事角色定位 / Story Role",
                STORY_ROLE_OPTIONS,
                index=_guided_index(STORY_ROLE_OPTIONS, draft.story_role),
            )
            role_detail = st.text_area(
                "角色定位补充 / Role Detail（可选）",
                value=draft.story_role_description,
                placeholder="例如：平时胆小，但看到 Portal 会第一个进去",
                height=90,
            )

        if st.button("Next → 继续", type="primary", use_container_width=True):
            st.session_state.char_name = name
            st.session_state.char_draft = draft.model_copy(update={
                "character_type": character_type,
                "character_type_description": type_detail,
                "age": age,
                "story_role": story_role,
                "story_role_description": role_detail,
            })
            go(1)
        return

    # ------------------------------------------------------------------
    # Stage 2: look
    # ------------------------------------------------------------------
    if stage == 1:
        st.markdown("### 🎨 TA 长什么样？")
        c1, c2 = st.columns(2)
        with c1:
            appearance = st.text_area(
                "外形 / Appearance",
                value=draft.appearance,
                placeholder="例如：大大的头、圆圆的脸、软软的轮廓",
                height=95,
            )
            hair_or_fur = st.text_input(
                "头发 / 毛发特征 / Hair or Fur",
                value=draft.hair_or_fur,
                placeholder="蓬松短毛、柔软卷发、机械纤维……",
            )
            hair_style = st.selectbox(
                "发型 / Hairstyle",
                HAIRSTYLE_OPTIONS,
                index=_select_index(HAIRSTYLE_OPTIONS, draft.hair_style),
            )
            hair_name = st.text_input(
                "颜色名字 / Hair Color Name（可选）",
                value=draft.hair_or_fur_color,
                placeholder="例如：焦糖棕",
            )
            hair_hex = st.color_picker(
                "真正使用的头发 / 毛发颜色",
                value=draft.hair_or_fur_color_hex,
                key="hair_color_sample",
                help="这个色块是生成图片时的颜色 source of truth。",
            )

        with c2:
            body_build = st.selectbox(
                "体型 / Body Build",
                BODY_BUILD_OPTIONS,
                index=_select_index(BODY_BUILD_OPTIONS, draft.body_build),
            )
            eye_name = st.text_input(
                "眼睛颜色名字 / Eye Color Name（可选）",
                value=draft.eyes.color,
                placeholder="例如：焦糖棕",
            )
            eye_hex = st.color_picker(
                "真正使用的眼睛颜色",
                value=draft.eyes.color_hex,
                key="eye_color_sample",
                help="这个色块是生成图片时的颜色 source of truth。",
            )
            favorite_colors = st.text_input(
                "最喜欢的颜色 / Favorite Colors",
                value="，".join(draft.favorite_colors),
                placeholder="粉色，薄荷绿，薰衣草紫",
            )
            favs = list(draft.favorite_color_hexes[:3] or DEFAULT_FAVORITE_COLOR_HEXES)
            while len(favs) < 3:
                favs.append(DEFAULT_FAVORITE_COLOR_HEXES[len(favs)])
            f1, f2, f3 = st.columns(3)
            with f1:
                fav1 = st.color_picker("Color 1", favs[0], key="fav_color_1")
            with f2:
                fav2 = st.color_picker("Color 2", favs[1], key="fav_color_2")
            with f3:
                fav3 = st.color_picker("Color 3", favs[2], key="fav_color_3")
            distinctive = st.text_input(
                "特别特征 / Distinctive Feature",
                value="，".join(draft.distinctive_features),
                placeholder="例如：左脸有一颗小星星",
            )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", use_container_width=True):
                go(0)
        with nxt:
            if st.button("Next → 继续", type="primary", use_container_width=True):
                st.session_state.char_draft = draft.model_copy(update={
                    "appearance": appearance,
                    "hair_or_fur": hair_or_fur,
                    "hair_style": hair_style,
                    "hair_or_fur_color": hair_name,
                    "hair_or_fur_color_hex": hair_hex,
                    "body_build": body_build,
                    "eyes": draft.eyes.model_copy(update={
                        "color": eye_name,
                        "color_hex": eye_hex,
                    }),
                    "favorite_colors": split_items(favorite_colors),
                    "favorite_color_hexes": [fav1, fav2, fav3],
                    "distinctive_features": split_items(distinctive),
                })
                go(2)
        return

    # ------------------------------------------------------------------
    # Stage 3: personality
    # ------------------------------------------------------------------
    if stage == 2:
        st.markdown("### 💬 TA 是什么性格？")
        c1, c2 = st.columns(2)
        with c1:
            personality = st.text_input(
                "性格 / Personality",
                value="，".join(draft.personality_traits),
                placeholder="好奇，勇敢，有点害羞",
            )
            strengths = st.text_input("擅长 / Strengths", value="，".join(draft.strengths))
            weaknesses = st.text_input("弱点 / Weaknesses", value="，".join(draft.weaknesses))
            fears = st.text_input("害怕什么 / Fears", value="，".join(draft.fears))
        with c2:
            tone = st.text_input(
                "说话语气 / Speaking Tone",
                value=draft.speaking_tone,
                placeholder="温柔、兴奋、慢慢的……",
            )
            language = st.text_input(
                "母语 / Native Language",
                value=draft.native_language or "中文",
            )
            english = st.slider(
                "英语水平 / English Level",
                1, 10, value=draft.english_level or 5,
            )
            st.info(english_level_label(english))

        with st.expander("✨ More personality details / 更多性格细节", expanded=False):
            habits = st.text_input("小习惯 / Habits", value="，".join(draft.habits))
            likes = st.text_input("喜欢 / Likes", value="，".join(draft.likes))
            dislikes = st.text_input("不喜欢 / Dislikes", value="，".join(draft.dislikes))
            abilities = st.text_input("能力 / Abilities", value="，".join(draft.abilities))
            limitations = st.text_input("限制 / Limitations", value="，".join(draft.limitations))

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", use_container_width=True):
                go(1)
        with nxt:
            if st.button("Next → 继续", type="primary", use_container_width=True):
                st.session_state.char_draft = draft.model_copy(update={
                    "personality_traits": split_items(personality),
                    "strengths": split_items(strengths),
                    "weaknesses": split_items(weaknesses),
                    "fears": split_items(fears),
                    "speaking_tone": tone,
                    "native_language": language,
                    "english_level": english,
                    "habits": split_items(habits),
                    "likes": split_items(likes),
                    "dislikes": split_items(dislikes),
                    "abilities": split_items(abilities),
                    "limitations": split_items(limitations),
                })
                go(3)
        return

    # ------------------------------------------------------------------
    # Stage 4: size and outfit
    # ------------------------------------------------------------------
    if stage == 3:
        st.markdown("### 👕📏 TA 穿什么？有多高？")
        height = st.selectbox(
            "身高感觉 / Height Category",
            HEIGHT_OPTIONS,
            index=_select_index(HEIGHT_OPTIONS, draft.height),
        )

        resolved = ctx.references.resolved_anchors()
        if resolved:
            config, anchor_assets, anchor_heights = resolved
            minimum, maximum = config.height_bounds(anchor_heights)
            initial = float(draft.height_cm or sum(anchor_heights) / len(anchor_heights))
            initial = min(max(initial, minimum), maximum)
            height_cm = st.slider(
                "精确身高 / Exact Height",
                min_value=float(round(minimum, 1)),
                max_value=float(round(maximum, 1)),
                value=float(round(initial, 1)),
                step=1.0,
                format="%.0f cm",
            )
            names = [asset.display_name for asset in anchor_assets]
            render_height_ruler(
                minimum=minimum,
                maximum=maximum,
                height_cm=height_cm,
                anchor_names=names,
                anchor_heights=anchor_heights,
            )
        else:
            height_cm = st.number_input(
                "精确身高 / Exact Height (cm)",
                min_value=1.0,
                max_value=1000.0,
                value=float(draft.height_cm or 120.0),
                step=1.0,
            )
            st.caption("Studio 设置两个 Reference Anchors 后，这里会出现相对身高尺。")

        defaults = ctx.assets.ensure_default_character_wearables()
        wear_assets = ctx.repository.list_assets(AssetType.WEARABLE)
        top_assets = _wearables_for_slot(wear_assets, "top")
        bottom_assets = _wearables_for_slot(wear_assets, "bottom")
        shoes_assets = _wearables_for_slot(wear_assets, "shoes")
        hat_assets = _wearables_for_slot(wear_assets, "hat")

        st.caption("默认：白色 T恤 + 蓝色牛仔裤。以后可以在 Wearable Factory 增加更多衣服。")
        c1, c2 = st.columns(2)
        with c1:
            top = _asset_selector(
                "上衣 / Top",
                top_assets,
                draft.wearables.top_id or defaults["top"].asset_id,
                "wear_top",
            )
            bottom = _asset_selector(
                "下装 / Bottom",
                bottom_assets,
                draft.wearables.bottom_id or defaults["bottom"].asset_id,
                "wear_bottom",
            )
        with c2:
            shoes = _asset_selector("鞋子 / Shoes", shoes_assets, draft.wearables.shoes_id, "wear_shoes")
            hat = _asset_selector("帽子 / Hat", hat_assets, draft.wearables.hat_id, "wear_hat")

        prop_assets = ctx.repository.list_assets(AssetType.PROP)
        selected_props = st.multiselect(
            "🎒 初始道具 / Starting Props（最多 2 个）",
            prop_assets,
            default=[p for p in prop_assets if p.asset_id in draft.starting_prop_ids],
            format_func=lambda asset: asset.display_name,
            max_selections=2,
        )

        with st.expander("🛠 Advanced body details / 高级身体细节", expanded=False):
            st.caption("🔒 Canon 比例：Mini Playable Avatar，约 2.8–3.0 头身。")
            body_type = st.text_input("身体类型 / Body Type", value=draft.body_type)
            proportions = st.text_input("特殊比例备注 / Proportion Notes", value=draft.proportions)
            face = st.text_input("脸部备注 / Face Notes", value=draft.face)
            eye_shape = st.text_input("眼睛形状 / Eye Shape", value=draft.eyes.shape or "round")
            eye_size = st.text_input("眼睛大小 / Eye Size", value=draft.eyes.size or "large")
            movement = st.text_input("动作风格 / Movement Style", value=draft.movement_style)

        back, nxt = st.columns([1, 2])
        with back:
            if st.button("← Back", use_container_width=True):
                go(2)
        with nxt:
            if st.button("Next → Create", type="primary", use_container_width=True):
                st.session_state.char_draft = draft.model_copy(update={
                    "height": height,
                    "height_cm": height_cm,
                    "body_type": body_type,
                    "proportions": proportions,
                    "face": face,
                    "eyes": draft.eyes.model_copy(update={
                        "shape": eye_shape,
                        "size": eye_size,
                    }),
                    "movement_style": movement,
                    "wearables": WearableLoadout(
                        top_id=top.asset_id if top else None,
                        bottom_id=bottom.asset_id if bottom else None,
                        shoes_id=shoes.asset_id if shoes else None,
                        hat_id=hat.asset_id if hat else None,
                        accessory_ids=draft.wearables.accessory_ids,
                    ),
                    "starting_prop_ids": [p.asset_id for p in selected_props],
                })
                go(4)
        return

    # ------------------------------------------------------------------
    # Stage 5: create + approve
    # ------------------------------------------------------------------
    final_profile = draft
    name = st.session_state.get("char_name", "").strip()
    missing = final_profile.missing_core_fields()

    st.markdown("### ✨ Ready to Create")
    left, right = st.columns([1, 1])
    with left:
        st.markdown(f"#### {escape(name) if name else 'New Character'}")
        st.write(final_profile.appearance or "还没有外形描述。")
        st.caption(f"Type · {final_profile.character_type or '—'}")
        st.caption(f"Role · {final_profile.story_role or '—'}")
        st.caption(f"Height · {final_profile.height_cm or '—'} cm")
        st.caption("Personality · " + (" · ".join(final_profile.personality_traits) or "—"))
    with right:
        palette = final_profile.favorite_color_hexes or DEFAULT_FAVORITE_COLOR_HEXES
        swatches = "".join(
            f'<span style="display:inline-block;width:34px;height:34px;border-radius:12px;'
            f'background:{color};margin:4px;border:1px solid rgba(0,0,0,.08)"></span>'
            for color in palette[:3]
        )
        st.markdown("#### 🎨 Palette")
        st.markdown(swatches, unsafe_allow_html=True)
        st.caption(
            f"Hair/Fur {final_profile.hair_or_fur_color_hex} · "
            f"Eyes {final_profile.eyes.color_hex}"
        )
        st.caption("🔒 Canon · Mini Playable Avatar · 2.8–3.0 heads tall")

    if missing:
        st.warning("还差这些核心设定：" + ", ".join(missing))
    if not name:
        st.warning("还没有名字。返回 Step 1 给 TA 取一个名字。")

    count = int(st.session_state.get("creator_generation_count", 0))
    remaining = max(0, MAX_GENERATIONS_PER_SESSION - count)
    st.caption(f"🎟️ 本次浏览器会话还可以生成 {remaining}/{MAX_GENERATIONS_PER_SESSION} 次。")

    candidate_path = st.session_state.get("character_master_candidate_path")
    generate_label = "✨ Generate Master Sheet / 生成角色设定图" if not candidate_path else "🎲 Regenerate / 再来一个"

    back, generate = st.columns([1, 2])
    with back:
        if st.button("← Back to Edit", use_container_width=True):
            go(3)
    with generate:
        if st.button(
            generate_label,
            type="primary",
            disabled=bool(missing) or not name or not ctx.character_masters.is_available or remaining <= 0,
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

        art, facts = st.columns([2.1, 1])
        with art:
            try:
                st.image(
                    ctx.storage.get_bytes(candidate_path),
                    caption="Visual Master · Hero + Turnaround + Expressions",
                    use_container_width=True,
                )
            except Exception:
                st.warning("角色图片暂时无法读取，可以点击 Regenerate 再试一次。")

        with facts:
            st.markdown("#### 📋 Canon Profile")
            st.write(f"**Name** · {name}")
            st.write(f"**Type** · {final_profile.character_type}")
            st.write(f"**Age** · {final_profile.age}")
            st.write(f"**Role** · {final_profile.story_role or '—'}")
            st.write(f"**Height** · {final_profile.height_cm:.0f} cm" if final_profile.height_cm else "**Height** · —")
            st.write(f"**Hair/Fur** · {final_profile.hair_or_fur_color or final_profile.hair_or_fur_color_hex}")
            st.write(f"**Eyes** · {final_profile.eyes.color or final_profile.eyes.color_hex}")
            st.write("**Personality** · " + (" · ".join(final_profile.personality_traits) or "—"))
            st.caption("所有文字来自结构化 Character Profile，不由图片模型生成。")

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
                st.success(f"角色正式加入 Mini Utopia！ · {candidate_character_id}")
                st.balloons()
            except Exception as exc:
                st.error(f"保存失败 / Approval failed: {exc}")

    if not ctx.character_masters.is_available:
        st.info("Image API 尚未连接；目前只能保存 Profile。")
