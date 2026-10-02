from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from studio.core.enums import AssetType
from studio.models.character import (
    CharacterProfile,
    EyeProfile,
    WearableLoadout,
)
from studio.models.reference import ReferenceCharacterConfig


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
    st.markdown(
        """
        <style>
        .mu-step-card {
            border-radius: 24px;
            padding: 18px 20px 8px 20px;
            margin: 12px 0 18px 0;
            background: linear-gradient(135deg, rgba(255,248,221,.72), rgba(238,246,255,.82));
            border: 1px solid rgba(113, 103, 180, .12);
        }
        .mu-step-kicker {
            font-size: .82rem;
            font-weight: 750;
            letter-spacing: .04em;
            color: #7869b8;
            text-transform: uppercase;
        }
        .mu-ruler-wrap {
            margin: 12px 0 34px 0;
            padding: 18px 20px 48px 20px;
            border-radius: 22px;
            background: linear-gradient(135deg, #fff6d8, #f4e9ff 52%, #e7f7ff);
            border: 1px solid rgba(108,92,231,.12);
        }
        .mu-ruler-scale {
            display:flex;
            justify-content:space-between;
            font-size:.78rem;
            color:#76748b;
            margin-bottom:20px;
        }
        .mu-ruler-track {
            height:12px;
            border-radius:999px;
            position:relative;
            background:linear-gradient(90deg,#BDEFD7,#FFE0A8,#F6BEDC,#CDB4FF,#BDE7FF);
            box-shadow: inset 0 1px 2px rgba(52,46,86,.08);
        }
        .mu-ruler-marker {
            position:absolute;
            transform:translateX(-50%);
            top:-5px;
            text-align:center;
            min-width:110px;
        }
        .mu-ruler-dot {
            width:22px;
            height:22px;
            border-radius:50%;
            margin:0 auto;
            border:3px solid white;
            box-shadow:0 4px 14px rgba(60,52,94,.16);
        }
        .mu-ruler-label {
            margin-top:6px;
            font-size:.72rem;
            line-height:1.25;
            color:#53516b;
            background:rgba(255,255,255,.78);
            border-radius:10px;
            padding:4px 7px;
        }
        .mu-current .mu-ruler-label {
            color:#963b63;
            font-weight:650;
        }
        .mu-review {
            border-radius:24px;
            padding:20px 22px;
            background:linear-gradient(135deg,rgba(255,232,239,.75),rgba(237,245,255,.85));
            border:1px solid rgba(244,143,177,.22);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("✨ Character Factory / 角色工坊")
    st.caption(
        "你负责想象，Mini Utopia Studio 负责把想法整理成可以长期使用的角色。"
    )

    if studio_mode:
        render_reference_settings(ctx)

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 1 · IMAGINE / 想象</div>'
        '<h3>✨ 你想创造谁？</h3></div>',
        unsafe_allow_html=True,
    )
    description = st.text_area(
        "像讲故事一样描述 TA / Describe your character",
        value=st.session_state.get("char_source", ""),
        placeholder=(
            "例如：一只胖胖的大熊猫，戴黄色帽子，喜欢收集星星。"
            "他有点胆小，但一看到新的 Portal 就忍不住想进去看看。"
        ),
        height=130,
        key="character_source_text",
    )

    if st.button(
        "✨ Help Me Understand / 帮我整理",
        type="primary",
        disabled=not description.strip(),
    ):
        st.session_state.char_source = description
        st.session_state.char_draft = character_factory.parse_description(description)
        st.session_state.char_name = ""

    draft: CharacterProfile | None = st.session_state.get("char_draft")
    if not draft:
        return

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 2 · WHO ARE THEY? / TA是谁</div>'
        '<h3>👤 先认识 TA</h3></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input(
            "名字 / Name",
            value=st.session_state.get("char_name", ""),
            placeholder="给角色取一个名字",
            key="character_name_input",
        )
        st.session_state.char_name = name
        character_type = st.text_input(
            "TA是什么？ / Character Type",
            value=draft.character_type,
            placeholder="人类、大熊猫、机器人、云朵生物……",
        )
    with c2:
        age = st.text_input(
            "年龄 / Age",
            value=draft.age,
            placeholder="例如：8、teen、ageless",
        )
        story_role = st.text_input(
            "故事角色定位 / Story Role（可选）",
            value=draft.story_role,
            placeholder="Traveler、Explorer、Inventor……",
        )

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 3 · LOOK / TA长什么样</div>'
        '<h3>🎨 把 TA 画进脑海里</h3></div>',
        unsafe_allow_html=True,
    )
    a1, a2 = st.columns(2)
    with a1:
        appearance = st.text_area(
            "外形 / Appearance",
            value=draft.appearance,
            height=90,
        )
        hair_or_fur = st.text_input(
            "头发 / 毛发 / Hair or Fur",
            value=draft.hair_or_fur,
        )
        hair_style = st.selectbox(
            "发型 / Hairstyle",
            HAIRSTYLE_OPTIONS,
            index=_select_index(HAIRSTYLE_OPTIONS, draft.hair_style),
        )
        hair_or_fur_color = st.text_input(
            "头发 / 毛发颜色 / Hair or Fur Color",
            value=draft.hair_or_fur_color,
        )
    with a2:
        body_build = st.selectbox(
            "体型 / Body Build",
            BODY_BUILD_OPTIONS,
            index=_select_index(BODY_BUILD_OPTIONS, draft.body_build),
        )
        eye_color = st.text_input(
            "眼睛颜色 / Eye Color",
            value=draft.eyes.color,
        )
        favorite_colors = st.text_input(
            "最喜欢的颜色 / Favorite Colors",
            value="，".join(draft.favorite_colors),
            placeholder="粉色，薄荷绿，薰衣草紫……",
            help="喜欢的颜色不等于最终服装色。Mini Utopia 会继续保持统一的马卡龙视觉语言。",
        )
        distinctive = st.text_input(
            "特别特征 / Distinctive Features",
            value="，".join(draft.distinctive_features),
            placeholder="例如：左脸有一颗小星星、耳朵会发光",
        )

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 4 · SIZE / TA有多高</div>'
        '<h3>📏 用熟悉的人来理解身高</h3></div>',
        unsafe_allow_html=True,
    )
    height = st.selectbox(
        "身高感觉 / Height Category",
        HEIGHT_OPTIONS,
        index=_select_index(HEIGHT_OPTIONS, draft.height),
    )

    resolved = ctx.references.resolved_anchors()
    if resolved:
        config, anchor_assets, anchor_heights = resolved
        minimum, maximum = config.height_bounds(anchor_heights)
        initial_height = float(
            draft.height_cm
            if draft.height_cm is not None
            else sum(anchor_heights) / len(anchor_heights)
        )
        initial_height = min(max(initial_height, minimum), maximum)
        height_cm = st.slider(
            "精确身高 / Exact Height",
            min_value=float(round(minimum, 1)),
            max_value=float(round(maximum, 1)),
            value=float(round(initial_height, 1)),
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
        st.success(relative_height_label(height_cm, names, anchor_heights))
    else:
        height_cm = st.number_input(
            "精确身高 / Exact Height (cm)",
            min_value=1.0,
            max_value=1000.0,
            value=float(draft.height_cm or 120.0),
            step=1.0,
        )
        st.caption(
            "💡 Studio 里设置两个 Reference Anchors 后，这里会变成可视化相对身高尺。"
        )

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 5 · PERSONALITY & VOICE / TA是什么性格</div>'
        '<h3>💬 TA会怎样说话、怎样面对世界？</h3></div>',
        unsafe_allow_html=True,
    )
    p1, p2 = st.columns(2)
    with p1:
        personality = st.text_input(
            "性格 / Personality",
            value="，".join(draft.personality_traits),
            placeholder="好奇，勇敢，有点害羞……",
        )
        strengths = st.text_input(
            "擅长 / Strengths",
            value="，".join(draft.strengths),
        )
        weaknesses = st.text_input(
            "弱点 / Weaknesses",
            value="，".join(draft.weaknesses),
        )
        fears = st.text_input(
            "害怕什么 / Fears",
            value="，".join(draft.fears),
        )
    with p2:
        speaking_tone = st.text_input(
            "说话语气 / Speaking Tone",
            value=draft.speaking_tone,
            placeholder="温柔、兴奋、慢慢的、有点害羞……",
        )
        native_language = st.text_input(
            "母语 / Native Language",
            value=draft.native_language,
            placeholder="中文 / Chinese",
        )
        english_level = st.slider(
            "英语水平 / English Level",
            min_value=1,
            max_value=10,
            value=draft.english_level or 5,
        )
        st.info(english_level_label(english_level))

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 6 · WEAR & CARRY / TA穿什么、带什么</div>'
        '<h3>👕🎒 给 TA 准备出发装备</h3></div>',
        unsafe_allow_html=True,
    )
    wear_assets = ctx.repository.list_assets(AssetType.WEARABLE)
    w1, w2 = st.columns(2)
    with w1:
        top = _asset_selector(
            "上衣 / Top", wear_assets, draft.wearables.top_id, "wear_top"
        )
        bottom = _asset_selector(
            "下装 / Bottom", wear_assets, draft.wearables.bottom_id, "wear_bottom"
        )
        shoes = _asset_selector(
            "鞋子 / Shoes", wear_assets, draft.wearables.shoes_id, "wear_shoes"
        )
    with w2:
        hat = _asset_selector(
            "帽子 / Hat", wear_assets, draft.wearables.hat_id, "wear_hat"
        )
        default_accessories = [
            a for a in wear_assets if a.asset_id in draft.wearables.accessory_ids
        ]
        accessories = st.multiselect(
            "配饰 / Accessories",
            wear_assets,
            default=default_accessories,
            format_func=lambda asset: asset.display_name,
        )
        if not wear_assets:
            st.caption("还没有 WEAR Assets。可以先空着，之后再添加服装库。")

    prop_assets = ctx.repository.list_assets(AssetType.PROP)
    selected_props = st.multiselect(
        "🎒 初始道具 / Starting Props（最多 2 个 / max 2）",
        prop_assets,
        default=[
            prop for prop in prop_assets
            if prop.asset_id in draft.starting_prop_ids
        ],
        format_func=lambda asset: asset.display_name,
        max_selections=2,
    )

    with st.expander("✨ More Details / 更多细节", expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            body_type = st.text_input("身体类型 / Body Type", value=draft.body_type)
            proportions = st.text_input("身体比例 / Proportions", value=draft.proportions)
            face = st.text_input("脸部 / Face", value=draft.face)
            eye_shape = st.text_input("眼睛形状 / Eye Shape", value=draft.eyes.shape)
            eye_size = st.text_input("眼睛大小 / Eye Size", value=draft.eyes.size)
            eye_special = st.text_input(
                "眼睛特别特征 / Eye Special Features",
                value="，".join(draft.eyes.special_features),
            )
            skin_fur_material = st.text_input(
                "皮肤 / 毛发 / 材质 / Skin, Fur or Material",
                value=draft.skin_fur_material,
            )
        with d2:
            habits = st.text_input("小习惯 / Habits", value="，".join(draft.habits))
            likes = st.text_input("喜欢 / Likes", value="，".join(draft.likes))
            dislikes = st.text_input("不喜欢 / Dislikes", value="，".join(draft.dislikes))
            abilities = st.text_input("能力 / Abilities", value="，".join(draft.abilities))
            limitations = st.text_input(
                "限制 / Limitations", value="，".join(draft.limitations)
            )
            movement_style = st.text_input(
                "动作风格 / Movement Style", value=draft.movement_style
            )

    final_profile = draft.model_copy(
        update={
            "source_description": st.session_state.get("char_source", description),
            "character_type": character_type,
            "age": age,
            "appearance": appearance,
            "hair_or_fur": hair_or_fur,
            "hair_style": hair_style,
            "hair_or_fur_color": hair_or_fur_color,
            "body_build": body_build,
            "height": height,
            "height_cm": height_cm,
            "favorite_colors": split_items(favorite_colors),
            "personality_traits": split_items(personality),
            "speaking_tone": speaking_tone,
            "native_language": native_language,
            "english_level": english_level,
            "story_role": story_role,
            "body_type": body_type,
            "proportions": proportions,
            "face": face,
            "eyes": EyeProfile(
                shape=eye_shape,
                color=eye_color,
                size=eye_size,
                special_features=split_items(eye_special),
            ),
            "skin_fur_material": skin_fur_material,
            "distinctive_features": split_items(distinctive),
            "strengths": split_items(strengths),
            "weaknesses": split_items(weaknesses),
            "fears": split_items(fears),
            "habits": split_items(habits),
            "likes": split_items(likes),
            "dislikes": split_items(dislikes),
            "abilities": split_items(abilities),
            "limitations": split_items(limitations),
            "movement_style": movement_style,
            "wearables": WearableLoadout(
                top_id=top.asset_id if top else None,
                bottom_id=bottom.asset_id if bottom else None,
                shoes_id=shoes.asset_id if shoes else None,
                hat_id=hat.asset_id if hat else None,
                accessory_ids=[asset.asset_id for asset in accessories],
            ),
            "starting_prop_ids": [prop.asset_id for prop in selected_props],
        }
    )

    st.markdown(
        '<div class="mu-step-card"><div class="mu-step-kicker">STEP 7 · REVIEW & SAVE / 看一看再保存</div>'
        '<h3>❤️ 这就是 TA</h3></div>',
        unsafe_allow_html=True,
    )
    missing = final_profile.missing_core_fields()

    with st.container(border=True):
        st.markdown(f"### {escape(name) if name else '✨ New Character'}")
        summary_cols = st.columns(3)
        summary_cols[0].metric("TA是什么", character_type or "—")
        summary_cols[1].metric("身高", f"{height_cm:.0f} cm")
        summary_cols[2].metric("英语", f"{english_level}/10")
        st.write(appearance or "还没有外形描述。")
        if final_profile.personality_traits:
            st.caption("性格 · " + " · ".join(final_profile.personality_traits))
        if final_profile.favorite_colors:
            st.caption("喜欢的颜色 · " + " · ".join(final_profile.favorite_colors))
        st.caption(
            "🎨 Canon characters automatically inherit Mini Utopia Visual DNA: "
            "Miniature · Block-inspired · Toy-like · Macaron Dreamscape · Cinematic"
        )

    if missing:
        st.warning(
            "还有核心设定没有完成 / Core fields still missing: "
            + ", ".join(missing)
        )

    if st.button(
        "❤️ Save This Character / 保存角色",
        type="primary",
        disabled=(not name.strip()) or bool(missing),
        use_container_width=True,
    ):
        asset = character_factory.save_character(
            name=name,
            description=st.session_state.get("char_source", description),
            profile=final_profile,
        )
        st.success(f"保存成功：{asset.display_name} · {asset.asset_id}")
        st.balloons()
        st.session_state.char_draft = None
        st.session_state.char_source = ""
        st.session_state.char_name = ""
        st.caption(
            "下一阶段会把 Master Reference、Front / Side / Back、"
            "表情和姿势都挂在这个永久 CHAR_ID 下。"
        )
