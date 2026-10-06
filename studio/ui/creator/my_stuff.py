from __future__ import annotations

from collections import Counter

import streamlit as st

from studio.core.enums import AssetType, ReviewStatus
from studio.models.character import CharacterProfile
from studio.models.equipment import (
    EquipmentRarity,
    EquipmentSlot,
    PLAYABLE_EQUIPMENT_SLOTS,
    StatBlock,
)
from studio.services.baby_service import BabyService
from studio.services.combat_drop_service import CombatDropService
from studio.ui.theme import render_game_hero


RARITY_META = {
    EquipmentRarity.GREEN: ("🟢", "Green"),
    EquipmentRarity.BLUE: ("🔵", "Blue"),
    EquipmentRarity.PURPLE: ("🟣", "Purple"),
    EquipmentRarity.GOLD: ("🟡", "Gold"),
    EquipmentRarity.RED: ("🔴", "Red"),
    EquipmentRarity.RAINBOW: ("🌈", "Rainbow"),
}


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


def _stat_line(stats: StatBlock) -> str:
    return f"❤️ HP +{stats.hp} · ⚔️ ATK +{stats.atk} · 🛡️ DEF +{stats.defense}"


def _stat_delta(current: StatBlock, new: StatBlock) -> str:
    def arrow(value: int) -> str:
        if value > 0:
            return f"↑ +{value}"
        if value < 0:
            return f"↓ {value}"
        return "→ 0"

    return (
        f"❤️ {arrow(new.hp - current.hp)} · "
        f"⚔️ {arrow(new.atk - current.atk)} · "
        f"🛡️ {arrow(new.defense - current.defense)}"
    )


def render_my_stuff(ctx) -> None:
    render_game_hero(
        "My Stuff 🎒✨",
        "这是你的收藏柜。装备属于你的 Collection，可以换给不同角色使用。",
        kicker="COLLECT · EQUIP · GROW",
    )

    claimed_rewards = CombatDropService(
        ctx.repository,
        equipment=ctx.equipment,
    ).claim_available()
    for reward in claimed_rewards:
        st.success(
            "🎁 Battle Reward / 战斗奖励 · "
            f"{reward.display_name} · {reward.rarity.value.title()} · "
            "已放入 My Stuff"
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

    collection = ctx.equipment.ensure_starter_collection()
    definitions = ctx.equipment.list_definitions()

    selected_character = st.selectbox(
        "Choose Character / 选择角色",
        characters,
        format_func=lambda asset: asset.display_name,
        key="my_stuff_character",
    )
    profile = CharacterProfile.model_validate(
        selected_character.metadata.get("character_profile", {})
    )
    active_baby = BabyService(ctx.repository).active_baby()
    loadout = collection.loadout_for(selected_character.asset_id)
    base_stats = ctx.equipment.base_stats(selected_character.asset_id)
    final_stats = ctx.equipment.final_stats(selected_character.asset_id)

    top_left, top_right = st.columns([1, 1], gap="large")

    with top_left:
        st.markdown(f"### 🎭 {selected_character.display_name}")
        st.caption(
            f"{profile.avatar.body_type.value.title()} · "
            f"{profile.avatar.species_head_id.replace('species_head_', '').replace('_v1', '').title()}"
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("❤️ HP", final_stats.hp, final_stats.hp - base_stats.hp)
        c2.metric("⚔️ ATK", final_stats.atk, final_stats.atk - base_stats.atk)
        c3.metric("🛡️ DEF", final_stats.defense, final_stats.defense - base_stats.defense)
        st.caption(
            f"Base · HP {base_stats.hp} / ATK {base_stats.atk} / DEF {base_stats.defense}"
        )
        if active_baby is not None:
            st.info(
                f"🐣 Active Baby · {active_baby.display_name} · "
                f"Lv.{active_baby.level} · ✨ XP {active_baby.xp} · "
                f"💞 Bond {active_baby.bond}"
            )
        else:
            st.caption("🐣 No Active Baby yet · visit My Baby to meet one.")

    with top_right:
        st.markdown("### Equipped / 当前装备")
        for slot in PLAYABLE_EQUIPMENT_SLOTS:
            item_id = loadout.item_id_for_slot(slot)
            if not item_id:
                st.write(f"{SLOT_LABELS[slot]} · —")
                continue
            item = collection.item_by_id(item_id)
            definition = definitions.get(item.definition_id) if item else None
            if item is None or definition is None:
                st.write(f"{SLOT_LABELS[slot]} · —")
                continue
            emoji, rarity_name = RARITY_META[item.rarity]
            cols = st.columns([3, 1])
            cols[0].write(
                f"{SLOT_LABELS[slot]} · {emoji} **{definition.display_name}** · {rarity_name}"
            )
            if cols[1].button(
                "Unequip",
                key=f"unequip_{selected_character.asset_id}_{slot.value}",
                use_container_width=True,
            ):
                ctx.equipment.unequip(
                    character_asset_id=selected_character.asset_id,
                    slot=slot,
                )
                st.rerun()

    st.divider()

    rarity_counts = Counter(item.rarity for item in collection.items)
    a, b, c, d = st.columns(4)
    a.metric("🎒 Owned", len(collection.items))
    b.metric("🟢 Green", rarity_counts[EquipmentRarity.GREEN])
    c.metric("🔵 Blue", rarity_counts[EquipmentRarity.BLUE])
    d.metric("🟣 Purple+", sum(
        rarity_counts[rarity]
        for rarity in (
            EquipmentRarity.PURPLE,
            EquipmentRarity.GOLD,
            EquipmentRarity.RED,
            EquipmentRarity.RAINBOW,
        )
    ))

    st.markdown("### Collection / 我的收藏")
    filter_a, filter_b = st.columns(2)
    with filter_a:
        slot_filter = st.selectbox(
            "Slot / 类型",
            ["all", *[slot.value for slot in PLAYABLE_EQUIPMENT_SLOTS]],
            format_func=lambda value: (
                "All / 全部"
                if value == "all"
                else SLOT_LABELS[EquipmentSlot(value)]
            ),
            key="my_stuff_slot_filter",
        )
    with filter_b:
        rarity_filter = st.selectbox(
            "Rarity / 稀有度",
            ["all", *[rarity.value for rarity in EquipmentRarity]],
            format_func=lambda value: (
                "All / 全部"
                if value == "all"
                else (
                    RARITY_META[EquipmentRarity(value)][0]
                    + " "
                    + RARITY_META[EquipmentRarity(value)][1]
                )
            ),
            key="my_stuff_rarity_filter",
        )

    visible_items = []
    for item in collection.items:
        definition = definitions.get(item.definition_id)
        if definition is None:
            continue
        if slot_filter != "all" and definition.slot.value != slot_filter:
            continue
        if rarity_filter != "all" and item.rarity.value != rarity_filter:
            continue
        visible_items.append((item, definition))

    if not visible_items:
        st.info("这个筛选条件下还没有装备。")
        return

    for item, definition in visible_items:
        equipped_id = loadout.item_id_for_slot(definition.slot)
        current_item = collection.item_by_id(equipped_id) if equipped_id else None
        current_stats = (
            current_item.rolled_stats
            if current_item is not None
            else StatBlock()
        )
        emoji, rarity_name = RARITY_META[item.rarity]

        with st.container(border=True):
            title_col, action_col = st.columns([3, 1])
            with title_col:
                st.markdown(
                    f"#### {emoji} {definition.display_name} · {rarity_name}"
                )
                st.caption(SLOT_LABELS[definition.slot])
                st.write(_stat_line(item.rolled_stats))
                if equipped_id == item.item_instance_id:
                    st.success("Equipped / 已装备")
                else:
                    st.caption(
                        "Compared with current · "
                        + _stat_delta(current_stats, item.rolled_stats)
                    )
            with action_col:
                if equipped_id == item.item_instance_id:
                    if st.button(
                        "Unequip / 卸下",
                        key=f"card_unequip_{item.item_instance_id}",
                        use_container_width=True,
                    ):
                        ctx.equipment.unequip(
                            character_asset_id=selected_character.asset_id,
                            slot=definition.slot,
                        )
                        st.rerun()
                else:
                    if st.button(
                        "Equip / 装备",
                        key=f"equip_{item.item_instance_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            ctx.equipment.equip(
                                character_asset_id=selected_character.asset_id,
                                item_instance_id=item.item_instance_id,
                            )
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

            st.caption(
                f"Item ID · {item.item_instance_id} · "
                f"Seed · {item.generation_seed}"
            )
