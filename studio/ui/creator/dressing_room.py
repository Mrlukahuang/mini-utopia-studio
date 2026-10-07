from __future__ import annotations

import streamlit as st

from studio.core.enums import AssetType, ReviewStatus
from studio.models.character import CharacterProfile
from studio.models.equipment import (
    EquipmentRarity,
    EquipmentSlot,
    PLAYABLE_EQUIPMENT_SLOTS,
)
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.play_session_service import CreatorPlaySessionService
from studio.ui.creator.avatar_preview import render_avatar_preview
from studio.ui.theme import render_game_hero


SLOT_LABELS = {
    EquipmentSlot.TOP: "👕 Top / 上衣",
    EquipmentSlot.BOTTOM: "👖 Bottom / 裤子",
    EquipmentSlot.SHOES: "👟 Shoes / 鞋子",
    EquipmentSlot.HEADWEAR: "👑 Headwear / 帽子·皇冠",
    EquipmentSlot.WEAPON_MAIN: "⚔️ Main Hand / 主手",
    EquipmentSlot.WEAPON_OFFHAND: "🛡️ Offhand / 副手·盾牌",
    EquipmentSlot.BACKPACK: "🎒 Backpack / 背包",
    EquipmentSlot.WINGS: "🪽 Wings / 翅膀",
    EquipmentSlot.ACCESSORY: "✨ Accessory / 饰品",
}

RARITY_EMOJI = {
    EquipmentRarity.GREEN: "🟢",
    EquipmentRarity.BLUE: "🔵",
    EquipmentRarity.PURPLE: "🟣",
    EquipmentRarity.GOLD: "🟡",
    EquipmentRarity.RED: "🔴",
    EquipmentRarity.RAINBOW: "🌈",
}


def render_dressing_room(ctx) -> None:
    render_game_hero(
        "Dressing Room 🪞✨",
        "给角色换装备，看属性变化，再带着 Active Baby 一起出发。",
        kicker="AVATAR · EQUIPMENT · BABY",
    )

    characters = [
        asset
        for asset in ctx.repository.list_assets(AssetType.CHARACTER)
        if asset.status != ReviewStatus.ARCHIVED
        and "character_profile" in asset.metadata
    ]
    if not characters:
        st.info("还没有 Character。先去 Character Factory 创建一个角色。")
        return

    equipment = EquipmentService(ctx.repository)
    babies = BabyService(ctx.repository)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()

    active_quest_id = st.session_state.get("active_quest_id")
    active_quest = (
        ctx.repository.get_quest(active_quest_id)
        if active_quest_id
        else None
    )
    if active_quest_id and active_quest is None:
        st.session_state.pop("active_quest_id", None)

    selected_character = st.selectbox(
        "Choose Character / 选择角色",
        characters,
        format_func=lambda asset: asset.display_name,
        key="dressing_room_character",
    )
    profile = CharacterProfile.model_validate(
        selected_character.metadata.get("character_profile", {})
    )

    # Resolve runtime state before rendering so the stage and controls read the
    # exact same persisted loadout.
    equipment_spec = equipment.runtime_spec(selected_character.asset_id)
    baby_spec = babies.runtime_spec()
    base_stats = equipment.base_stats(selected_character.asset_id)
    final_stats = equipment_spec.final_stats

    stage_col, control_col = st.columns([1.72, 1.0], gap="large")

    with stage_col:
        render_avatar_preview(
            profile.avatar,
            title="Dressing Room 3D / 试衣间实时预览",
            equipment=equipment_spec,
            baby=baby_spec,
            height=700,
        )

    with control_col:
        st.markdown(f"### 🎭 {selected_character.display_name}")
        st.caption(
            f"{profile.avatar.body_type.value.title()} · "
            f"{profile.avatar.species_head_id.replace('species_head_', '').replace('_v1', '').title()}"
        )

        hp_col, atk_col, def_col = st.columns(3)
        hp_col.metric("❤️ HP", final_stats.hp, final_stats.hp - base_stats.hp)
        atk_col.metric("⚔️ ATK", final_stats.atk, final_stats.atk - base_stats.atk)
        def_col.metric(
            "🛡️ DEF",
            final_stats.defense,
            final_stats.defense - base_stats.defense,
        )

        if baby_spec is not None:
            st.success(
                f"🐣 Active Baby · {baby_spec.display_name} · Lv.{baby_spec.level}"
            )
        else:
            st.caption("🐣 No Active Baby yet · visit My Baby to meet one.")

        if active_quest is not None:
            st.info(
                f"📜 Active Quest · {active_quest.title} · "
                f"{len(active_quest.objectives)} objectives"
            )

        st.markdown("#### Quick Equip / 快速换装")
        loadout = collection.loadout_for(selected_character.asset_id)

        for slot in PLAYABLE_EQUIPMENT_SLOTS:
            current_id = loadout.item_id_for_slot(slot)
            slot_items = []
            for item in collection.items:
                definition = definitions.get(item.definition_id)
                if definition is not None and definition.slot == slot:
                    slot_items.append(item)

            option_ids: list[str | None] = [None] + [
                item.item_instance_id for item in slot_items
            ]

            def _format_item(item_id: str | None, *, _slot=slot) -> str:
                if item_id is None:
                    return "— None / 不装备"
                item = collection.item_by_id(item_id)
                if item is None:
                    return "Unknown"
                definition = definitions.get(item.definition_id)
                if definition is None:
                    return "Unknown"
                rarity = RARITY_EMOJI.get(item.rarity, "✨")
                stats = item.rolled_stats
                return (
                    f"{rarity} {definition.display_name} · "
                    f"HP+{stats.hp} ATK+{stats.atk} DEF+{stats.defense}"
                )

            selected_id = st.selectbox(
                SLOT_LABELS[slot],
                option_ids,
                index=(
                    option_ids.index(current_id)
                    if current_id in option_ids
                    else 0
                ),
                format_func=_format_item,
                key=f"dressing_{selected_character.asset_id}_{slot.value}",
            )

            # Streamlit reruns on selection. Persist only when the newly chosen
            # value differs from the stored CharacterLoadout.
            if selected_id != current_id:
                if selected_id is None:
                    equipment.unequip(
                        character_asset_id=selected_character.asset_id,
                        slot=slot,
                    )
                else:
                    equipment.equip(
                        character_asset_id=selected_character.asset_id,
                        item_instance_id=selected_id,
                    )
                st.rerun()

        st.caption(
            "这里和 My Stuff 使用同一份 CharacterLoadout；换装会持久保存，"
            "不是临时预览。"
        )

        play_sessions = CreatorPlaySessionService(
            ctx.repository,
            ctx.character_runtime,
            equipment=equipment,
            babies=babies,
        )
        if st.button(
            "🎮 Play This Loadout / 带这套装备出发",
            type="primary",
            use_container_width=True,
            key=f"play_loadout_{selected_character.asset_id}",
        ):
            try:
                play_sessions.export(
                    character_asset_id=selected_character.asset_id,
                    quest_id=(
                        active_quest.quest_id
                        if active_quest is not None
                        else None
                    ),
                )
                st.session_state.play_character_id = selected_character.asset_id
                if active_quest is not None:
                    st.session_state.selected_world_id = (
                        active_quest.world_asset_id
                    )
                st.session_state.pop("runtime_character_asset", None)
                st.session_state.pending_app_page = "🎮 Explore World"
                st.rerun()
            except Exception as exc:
                st.error(f"Play session export failed / 导出失败: {exc}")

        with st.expander("Current Runtime / 当前运行时", expanded=False):
            for slot in PLAYABLE_EQUIPMENT_SLOTS:
                item = equipment_spec.equipped.get(slot.value)
                if item is None:
                    st.write(f"{SLOT_LABELS[slot]} · —")
                else:
                    st.write(
                        f"{SLOT_LABELS[slot]} · "
                        f"{RARITY_EMOJI[item.rarity]} {item.display_name}"
                    )
            if baby_spec is not None:
                st.write(
                    f"🐣 {baby_spec.display_name} · "
                    f"{baby_spec.species_id} · Lv.{baby_spec.level}"
                )
