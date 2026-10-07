from __future__ import annotations

import streamlit as st

from studio.services.adventure_hub_service import AdventureHubService


RARITY_ICON = {
    "green": "🟢",
    "blue": "🔵",
    "purple": "🟣",
    "gold": "🟡",
    "red": "🔴",
    "rainbow": "🌈",
}


def render_adventure_hub(ctx) -> None:
    hub = AdventureHubService(ctx.repository).status()

    st.markdown("## 🧭 Adventure Hub / 冒险大厅")
    st.caption("继续正在发生的冒险，看看 Baby、奖励和世界今天变成什么样。")

    continue_col, baby_col = st.columns(2, gap="large")
    with continue_col:
        with st.container(border=True):
            st.markdown("### 🎮 Continue Adventure / 继续冒险")
            if hub.quest is not None:
                st.markdown(f"**📜 {hub.quest.title}**")
                st.caption(f"🌍 {hub.quest.world_name}")
            elif hub.world is not None:
                st.markdown(f"**🌍 {hub.world.world_name}**")
                st.caption("Free Explore / 自由探索")
            else:
                st.markdown("**还没有冒险世界**")
                st.caption("先去创造一个 Mini World。")

            if st.button(
                "▶ Continue / 继续",
                type="primary",
                use_container_width=True,
                key="hub_continue_adventure",
            ):
                if hub.quest is not None:
                    st.session_state.active_quest_id = hub.quest.quest_id
                    st.session_state.selected_world_id = hub.quest.world_asset_id
                elif hub.world is not None:
                    st.session_state.selected_world_id = hub.world.world_asset_id
                st.session_state.pending_app_page = hub.continue_page
                st.rerun()

    with baby_col:
        with st.container(border=True):
            st.markdown("### 🐣 Active Baby / 当前宝宝")
            if hub.baby is None:
                st.caption("还没有 Active Baby。")
                if st.button(
                    "Meet My Baby / 去领宝宝",
                    use_container_width=True,
                    key="hub_meet_baby",
                ):
                    st.session_state.pending_app_page = "🐣 My Baby"
                    st.rerun()
            else:
                st.markdown(f"**{hub.baby.display_name} · Lv.{hub.baby.level}**")
                st.progress(
                    min(1.0, (hub.baby.xp % 100) / 100),
                    text=f"✨ XP {hub.baby.xp} · 💞 Bond {hub.baby.bond}",
                )

    reward_col, world_col = st.columns(2, gap="large")
    with reward_col:
        with st.container(border=True):
            st.markdown("### 🎁 Latest Reward / 最新收获")
            if hub.latest_reward is None:
                st.caption("还没有收集到装备。")
            else:
                rarity = hub.latest_reward.rarity.value
                st.markdown(
                    f"**{RARITY_ICON.get(rarity, '✨')} "
                    f"{hub.latest_reward.display_name}**"
                )
                st.caption(rarity.title())
                if st.button(
                    "🎒 Open My Stuff / 打开收藏",
                    use_container_width=True,
                    key="hub_open_collection",
                ):
                    st.session_state.pending_app_page = "🎒 My Stuff"
                    st.rerun()

    with world_col:
        with st.container(border=True):
            st.markdown("### 🌍 World Progress / 世界进度")
            if hub.world is None:
                st.caption("等待第一个 World。")
            else:
                st.markdown(f"**{hub.world.world_name}**")
                mode_icon = {
                    "explore": "🧭",
                    "quest": "📜",
                    "story_play": "🎭",
                    "creative": "🎨",
                }
                st.caption(
                    " · ".join(
                        f"{mode_icon.get(mode, '✨')} {mode.replace('_', ' ').title()}"
                        for mode in hub.world.modes
                    )
                )
                a, b, c = st.columns(3)
                a.metric("Quest", hub.world.quest_count)
                b.metric("Story", hub.world.story_count)
                c.metric("Decor", hub.world.decoration_count)
