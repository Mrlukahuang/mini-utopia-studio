from __future__ import annotations

from html import escape
import streamlit as st

from studio.core.enums import AssetType
from studio.models.character import CharacterProfile
from studio.models.equipment import (
    EquipmentSlot,
    PLAYABLE_EQUIPMENT_SLOTS,
    StatBlock,
)
from studio.models.equipment_runtime import (
    EquipmentRuntimeItemSpec,
    EquipmentRuntimeSpec,
)
from studio.models.reference import ReferenceCharacterConfig
from studio.ui.creator.avatar_editor import (
    render_avatar_appearance_editor,
    reset_avatar_editor_state,
)
from studio.ui.creator.avatar_legacy_bridge import legacy_visual_updates
from studio.ui.creator.avatar_preview import render_avatar_preview
from studio.ui.creator.character_presets import (
    CUSTOM,
    AGE_OPTIONS,
    DISTINCTIVE_OPTIONS,
    FACE_STYLE_OPTIONS,
    FAVORITE_COLOR_HEX,
    FAVORITE_COLOR_OPTIONS,
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

FACTORY_CLOTHING_SLOTS = (
    EquipmentSlot.TOP,
    EquipmentSlot.BOTTOM,
    EquipmentSlot.SHOES,
    EquipmentSlot.HEADWEAR,
)
FACTORY_GEAR_SLOTS = (
    EquipmentSlot.WEAPON_MAIN,
    EquipmentSlot.WEAPON_OFFHAND,
    EquipmentSlot.BACKPACK,
    EquipmentSlot.WINGS,
    EquipmentSlot.ACCESSORY,
)
FACTORY_SLOT_LABELS = {
    EquipmentSlot.TOP: "👕 Top / 上衣",
    EquipmentSlot.BOTTOM: "👖 Bottom / 下装",
    EquipmentSlot.SHOES: "👟 Shoes / 鞋子",
    EquipmentSlot.HEADWEAR: "👑 Headwear / 帽子·皇冠",
    EquipmentSlot.WEAPON_MAIN: "⚔️ Main Hand / 主手",
    EquipmentSlot.WEAPON_OFFHAND: "🛡️ Offhand / 副手",
    EquipmentSlot.BACKPACK: "🎒 Backpack / 背包",
    EquipmentSlot.WINGS: "🪽 Wings / 翅膀",
    EquipmentSlot.ACCESSORY: "✨ Accessory / 饰品",
}
FACTORY_RARITY_EMOJI = {
    "green": "🟢",
    "blue": "🔵",
    "purple": "🟣",
    "gold": "🟡",
    "red": "🔴",
    "rainbow": "🌈",
}

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


def _factory_equipment_state(equipment_service):
    collection = equipment_service.ensure_starter_collection()
    definitions = equipment_service.list_definitions()
    return collection, definitions


def _factory_slot_items(collection, definitions, slot: EquipmentSlot):
    return [
        item
        for item in collection.items
        if (
            definitions.get(item.definition_id) is not None
            and definitions[item.definition_id].slot == slot
        )
    ]


def _factory_item_label(item_id, collection, definitions) -> str:
    if item_id is None:
        return "— None / 不装备 —"
    item = collection.item_by_id(item_id)
    if item is None:
        return "Unknown"
    definition = definitions.get(item.definition_id)
    if definition is None:
        return "Unknown"
    rarity = FACTORY_RARITY_EMOJI.get(item.rarity.value, "✨")
    stats = item.rolled_stats
    return (
        f"{rarity} {definition.display_name} · "
        f"HP+{stats.hp} ATK+{stats.atk} DEF+{stats.defense}"
    )


def _default_factory_equipment_selection(
    equipment_service,
    *,
    character_asset_id: str | None = None,
) -> dict[str, str | None]:
    collection, definitions = _factory_equipment_state(equipment_service)
    loadout = (
        collection.loadout_for(character_asset_id)
        if character_asset_id
        else None
    )
    selection: dict[str, str | None] = {}
    for slot in PLAYABLE_EQUIPMENT_SLOTS:
        persisted = loadout.item_id_for_slot(slot) if loadout else None
        if persisted is not None:
            selection[slot.value] = persisted
            continue
        items = _factory_slot_items(collection, definitions, slot)
        selection[slot.value] = (
            items[0].item_instance_id
            if slot in FACTORY_CLOTHING_SLOTS and items
            else None
        )
    return selection


def _build_factory_equipment_preview(
    equipment_service,
    appearance,
    selection: dict[str, str | None],
    *,
    character_asset_id: str = "CHAR_DRAFT",
) -> EquipmentRuntimeSpec:
    collection, definitions = _factory_equipment_state(equipment_service)
    total = StatBlock(hp=100, atk=10, defense=8)
    equipped: dict[str, EquipmentRuntimeItemSpec] = {}

    for slot in PLAYABLE_EQUIPMENT_SLOTS:
        item_id = selection.get(slot.value)
        if not item_id:
            continue
        item = collection.item_by_id(item_id)
        if item is None:
            continue
        definition = definitions.get(item.definition_id)
        if definition is None or definition.slot != slot:
            continue
        total = total.plus(item.rolled_stats)
        equipped[slot.value] = EquipmentRuntimeItemSpec(
            item_instance_id=item.item_instance_id,
            definition_id=definition.definition_id,
            display_name=definition.display_name,
            slot=definition.slot,
            rarity=item.rarity,
            mesh_asset_id=definition.mesh_asset_id,
            animation_class=definition.animation_class,
            rolled_stats=item.rolled_stats,
        )

    return EquipmentRuntimeSpec(
        character_asset_id=character_asset_id,
        body_type=appearance.body_type,
        final_stats=total,
        equipped=equipped,
    )


def _persist_factory_equipment_selection(
    equipment_service,
    *,
    character_asset_id: str,
    selection: dict[str, str | None],
) -> None:
    current = equipment_service.loadout_for(character_asset_id)
    for slot in PLAYABLE_EQUIPMENT_SLOTS:
        wanted = selection.get(slot.value)
        existing = current.item_id_for_slot(slot)
        if wanted == existing:
            continue
        if wanted is None:
            equipment_service.unequip(
                character_asset_id=character_asset_id,
                slot=slot,
            )
        else:
            equipment_service.equip(
                character_asset_id=character_asset_id,
                item_instance_id=wanted,
            )
        current = equipment_service.loadout_for(character_asset_id)


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


def reset_character_creation_state() -> None:
    """Clear only the active Character Builder state.

    Session-level generation accounting intentionally survives so Creator
    usage limits still apply across multiple characters in one session.
    """
    reset_avatar_editor_state()
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
        "char_equipment_selection",
    ):
        st.session_state.pop(key, None)

    for slot in PLAYABLE_EQUIPMENT_SLOTS:
        st.session_state.pop(f"factory_eq_{slot.value}", None)


def _start_over() -> None:
    reset_character_creation_state()
    st.rerun()


def render_character_factory(ctx, character_factory, *, studio_mode: bool = False) -> None:
    """Child-first Character Factory with an optional assisted prompt path."""

    render_game_hero(
        "Make Your Mini Hero ✨",
        "给 TA 取名字、捏外形、选性格，再穿上第一套衣服。完成后就会加入你的角色收藏。",
        kicker="CHARACTER FACTORY · MAKE A HERO",
    )

    if studio_mode:
        render_reference_settings(ctx)

    draft: CharacterProfile | None = st.session_state.get("char_draft")
    mode = st.session_state.get("char_creation_mode")

    if draft is None and mode is None:
        render_quest("先做一个属于你的 Mini Hero！ / Make a hero of your own!")
        st.markdown(
            '<div class="mu-world-card"><div class="emoji">🌟🧸</div>'
            '<h3>Start My Hero / 开始创造我的角色</h3>'
            '<p>名字 → 外形 → 性格 → 穿搭。一步一步选，随时都可以返回修改。</p></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "🌟 Start My Hero / 开始创造我的角色",
            key="start_my_hero",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.char_creation_mode = "custom"
            st.session_state.char_draft = CharacterProfile()
            st.session_state.char_stage = 0
            st.rerun()

        with st.expander(
            "✨ I already have an idea / 我想用一句话描述",
            expanded=False,
        ):
            st.caption(
                "如果你脑海里已经有角色，可以先描述一句，"
                "系统会帮你放进同一套可编辑选项里。"
            )
            if st.button(
                "✨ Describe My Hero / 用一句话开始",
                key="start_prompt_generate",
                use_container_width=True,
            ):
                st.session_state.char_creation_mode = "prompt"
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
        "1 · Name & Age / 名字和年龄",
        "2 · Look / 捏外形",
        "3 · Personality / 选性格",
        "4 · Outfit / 穿衣服",
        "5 · Ready / 完成",
    ]
    stage = max(0, min(int(st.session_state.get("char_stage", 0)), 4))
    st.progress((stage + 1) / 5, text=f"{stages[stage]} · {stage + 1}/5")
    st.caption("不用一次想完所有设定。先把你的英雄做出来，以后还可以继续换装和编辑。")

    def go(value: int) -> None:
        st.session_state.char_stage = max(0, min(value, 4))
        st.rerun()

    if stage == 0:
        st.markdown("### 👋 First, who are we making? / 先认识一下 TA")
        name = st.text_input(
            "🌟 Hero Name / 角色名字",
            value=st.session_state.get("char_name", ""),
            placeholder="给 TA 取一个名字",
            key="character_name_input",
        )
        age = st.selectbox(
            "🎂 Age / 年龄",
            AGE_OPTIONS,
            index=_preset_index(AGE_OPTIONS, draft.age, default=4),
        )

        with st.expander("✨ More choices / 更多设定（可选）", expanded=False):
            role = st.selectbox(
                "Story Role / 故事角色",
                STORY_ROLE_OPTIONS,
                index=_preset_index(
                    STORY_ROLE_OPTIONS,
                    draft.story_role,
                    default=0,
                ),
            )
            face = st.selectbox(
                "Face Style / 脸部感觉",
                FACE_STYLE_OPTIONS,
                index=_preset_index(
                    FACE_STYLE_OPTIONS,
                    draft.face,
                    default=0,
                ),
            )

        if draft.source_description:
            st.info("✨ 描述已经变成可编辑选项，你可以继续改成自己喜欢的样子。")

        if st.button(
            "Next → Make the Look / 下一步：捏外形",
            type="primary",
            disabled=not name.strip(),
            use_container_width=True,
        ):
            st.session_state.char_name = name
            st.session_state.char_draft = draft.model_copy(
                update={
                    "age": _choice(age, draft.age, AGE_OPTIONS),
                    "story_role": _choice(
                        role,
                        draft.story_role,
                        STORY_ROLE_OPTIONS,
                    ),
                    "face": _choice(face, draft.face, FACE_STYLE_OPTIONS),
                }
            )
            go(1)
        return

    if stage == 1:
        st.markdown("### 🎨 Look / TA 长什么样？")
        avatar = render_avatar_appearance_editor(draft.avatar)
        st.divider()
        st.markdown("#### ✨ Story Visual Details / 故事视觉细节")
        st.caption(
            "角色外观只在上方 Playable Avatar 选择一次；"
            "Master Image 和 Story 会自动沿用同一套外观。"
        )
        a, b = st.columns(2)
        with a:
            favorite_colors = st.multiselect(
                "Favorite Colors / 最喜欢的颜色（最多 3 个）",
                FAVORITE_COLOR_OPTIONS,
                default=[
                    value for value in draft.favorite_colors
                    if value in FAVORITE_COLOR_OPTIONS
                ][:3],
                max_selections=3,
            )
        with b:
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
                fav_hexes = [
                    FAVORITE_COLOR_HEX[value]
                    for value in favorite_colors
                    if value in FAVORITE_COLOR_HEX
                ]
                visual_updates = legacy_visual_updates(draft, avatar)
                st.session_state.char_draft = draft.model_copy(
                    update={
                        **visual_updates,
                        "favorite_colors": favorite_colors,
                        "favorite_color_hexes": (
                            fav_hexes or DEFAULT_FAVORITE_COLOR_HEXES
                        ),
                        "distinctive_features": (
                            [] if not distinctive else [distinctive]
                        ),
                    }
                )
                go(2)
        return

    if stage == 2:
        st.markdown("### 💬 What is your hero like? / TA 是什么性格？")
        personality_col, preview_col = st.columns(
            [1.0, 1.25],
            gap="large",
        )

        with personality_col:
            personality = st.multiselect(
                "🌈 Pick up to 3 / 选最多 3 个性格",
                PERSONALITY_OPTIONS,
                default=[
                    value for value in draft.personality_traits
                    if value in PERSONALITY_OPTIONS
                ][:3],
                max_selections=3,
            )
            tone = st.selectbox(
                "🗣️ Speaking Style / 说话感觉",
                SPEAKING_TONE_OPTIONS,
                index=_preset_index(
                    SPEAKING_TONE_OPTIONS,
                    draft.speaking_tone,
                    default=0,
                ),
            )

            with st.expander(
                "✨ More personality details / 更多性格设定（可选）"
            ):
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
                language = st.selectbox(
                    "Native Language / 母语",
                    LANGUAGE_OPTIONS,
                    index=_preset_index(
                        LANGUAGE_OPTIONS,
                        draft.native_language,
                        default=0,
                    ),
                )
                english = st.selectbox(
                    "English Level / 英语水平",
                    list(range(1, 11)),
                    index=max(0, min((draft.english_level or 5) - 1, 9)),
                    format_func=lambda level: (
                        f"{level} · {english_level_label(level)}"
                    ),
                )

        with preview_col:
            render_avatar_preview(
                draft.avatar,
                title="Your Hero / 你的角色",
                height=540,
            )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button(
                "← Back",
                key="personality_back",
                use_container_width=True,
            ):
                go(1)
        with nxt:
            if st.button(
                "Next → Outfit",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.char_draft = draft.model_copy(
                    update={
                        "personality_traits": personality,
                        "strengths": [] if not strength else [strength],
                        "weaknesses": [] if not weakness else [weakness],
                        "speaking_tone": _choice(
                            tone,
                            draft.speaking_tone,
                            SPEAKING_TONE_OPTIONS,
                        ),
                        "native_language": _choice(
                            language,
                            draft.native_language,
                            LANGUAGE_OPTIONS,
                        ),
                        "english_level": english,
                    }
                )
                go(3)
        return

    if stage == 3:
        st.markdown("### 👕 Outfit & Gear / 穿搭和装备")
        st.caption(
            "衣服和装备现在使用同一套 Equipment v2。右边会实时显示真正进入游戏的样子。"
        )

        collection, definitions = _factory_equipment_state(ctx.equipment)
        editing_id = st.session_state.get("editing_character_id")
        seed_selection = st.session_state.get("char_equipment_selection")
        if not isinstance(seed_selection, dict):
            seed_selection = _default_factory_equipment_selection(
                ctx.equipment,
                character_asset_id=editing_id,
            )

        selection = dict(seed_selection)
        controls_col, preview_col = st.columns(
            [1.0, 1.28],
            gap="large",
        )

        with controls_col:
            st.markdown("#### 👚 Clothes / 基础穿搭")
            for slot in FACTORY_CLOTHING_SLOTS:
                items = _factory_slot_items(
                    collection,
                    definitions,
                    slot,
                )
                option_ids = [None] + [
                    item.item_instance_id for item in items
                ]
                wanted = selection.get(slot.value)
                if wanted not in option_ids:
                    wanted = (
                        items[0].item_instance_id
                        if items
                        else None
                    )
                widget_key = f"factory_eq_{slot.value}"
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = wanted
                selected_id = st.selectbox(
                    FACTORY_SLOT_LABELS[slot],
                    option_ids,
                    format_func=lambda item_id, _c=collection, _d=definitions: (
                        _factory_item_label(item_id, _c, _d)
                    ),
                    key=widget_key,
                )
                selection[slot.value] = selected_id

            with st.expander(
                "⚔️ Adventure Gear / 冒险装备（可选）",
                expanded=False,
            ):
                for slot in FACTORY_GEAR_SLOTS:
                    items = _factory_slot_items(
                        collection,
                        definitions,
                        slot,
                    )
                    option_ids = [None] + [
                        item.item_instance_id for item in items
                    ]
                    wanted = selection.get(slot.value)
                    if wanted not in option_ids:
                        wanted = None
                    widget_key = f"factory_eq_{slot.value}"
                    if widget_key not in st.session_state:
                        st.session_state[widget_key] = wanted
                    selected_id = st.selectbox(
                        FACTORY_SLOT_LABELS[slot],
                        option_ids,
                        format_func=lambda item_id, _c=collection, _d=definitions: (
                            _factory_item_label(item_id, _c, _d)
                        ),
                        key=widget_key,
                    )
                    selection[slot.value] = selected_id

        preview_spec = _build_factory_equipment_preview(
            ctx.equipment,
            draft.avatar,
            selection,
            character_asset_id=editing_id or "CHAR_DRAFT",
        )

        with preview_col:
            render_avatar_preview(
                draft.avatar,
                title="Outfit Preview / 穿搭实时预览",
                equipment=preview_spec,
                height=620,
            )
            stats = preview_spec.final_stats
            stat_cols = st.columns(3)
            stat_cols[0].metric("❤️ HP", stats.hp)
            stat_cols[1].metric("⚔️ ATK", stats.atk)
            stat_cols[2].metric("🛡️ DEF", stats.defense)

        with st.expander(
            "✨ More details / 更多角色设定（可选）",
            expanded=False,
        ):
            height = st.selectbox(
                "Height Category / 身高感觉",
                HEIGHT_OPTIONS,
                index=_preset_index(
                    HEIGHT_OPTIONS,
                    draft.height,
                    default=2,
                ),
            )

            resolved = ctx.references.resolved_anchors()
            if resolved:
                config, anchor_assets, anchor_heights = resolved
                minimum, maximum = config.height_bounds(anchor_heights)
                initial = float(
                    draft.height_cm
                    or sum(anchor_heights) / len(anchor_heights)
                )
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
                    anchor_names=[
                        asset.display_name for asset in anchor_assets
                    ],
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

            prop_assets = ctx.repository.list_assets(AssetType.PROP)
            selected_props = st.multiselect(
                "Starting Props / 初始道具（最多 2 个）",
                prop_assets,
                default=[
                    prop
                    for prop in prop_assets
                    if prop.asset_id in draft.starting_prop_ids
                ],
                format_func=lambda asset: asset.display_name,
                max_selections=2,
            )
            extra = st.text_area(
                "✨ Extra Details / 额外补充",
                value=draft.creator_extra_details,
                placeholder="TA 来自哪里？有什么特别的小秘密或能力？",
                height=100,
            )

        back, nxt = st.columns([1, 2])
        with back:
            if st.button(
                "← Back",
                key="outfit_back",
                use_container_width=True,
            ):
                go(2)
        with nxt:
            if st.button(
                "Next → Ready / 下一步：完成",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.char_equipment_selection = selection
                st.session_state.char_draft = draft.model_copy(
                    update={
                        "height": _choice(
                            height,
                            draft.height,
                            HEIGHT_OPTIONS,
                        ),
                        "height_cm": height_cm,
                        "creator_extra_details": extra,
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

    st.markdown("### 🎉 Your Hero Is Ready! / 你的角色准备好啦")
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

    profile_can_save = not missing and bool(name)
    back, save = st.columns([1, 2])
    with back:
        if st.button("← Back to Edit / 返回修改", use_container_width=True):
            go(3)
    with save:
        if st.button(
            "💖 Save My Hero / 保存我的角色",
            type="primary",
            disabled=not profile_can_save,
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
                saved_character_id = asset.asset_id
                reset_character_creation_state()
                st.session_state.pending_app_page = "🎭 My Characters"
                st.session_state.last_saved_character_id = saved_character_id
                st.success("🌟 保存成功！你的角色已经加入 My Characters。")
                st.balloons()
                st.rerun()
            except Exception as exc:
                st.error(f"保存失败 / Save failed: {exc}")

    count = int(st.session_state.get("creator_generation_count", 0))
    remaining = max(0, MAX_GENERATIONS_PER_SESSION - count)
    candidate_path = st.session_state.get("character_master_candidate_path")

    with st.expander(
        "🎨 Optional Character Art / 可选：生成角色设定图",
        expanded=bool(candidate_path),
    ):
        if not ctx.character_masters.is_available:
            st.caption(
                "没有连接 Image API 也没关系。上面的 Save My Hero 可以直接保存可玩角色。"
            )
        else:
            st.caption(
                f"🎟️ 本次会话剩余生成次数：{remaining}/{MAX_GENERATIONS_PER_SESSION}"
            )
            if st.button(
                (
                    "✨ Generate Master Sheet / 生成角色设定图"
                    if not candidate_path
                    else "🎲 Regenerate / 再生成"
                ),
                disabled=(
                    not profile_can_save
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
                    reset_character_creation_state()
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

