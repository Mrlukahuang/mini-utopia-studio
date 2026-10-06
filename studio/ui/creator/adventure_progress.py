from __future__ import annotations

import streamlit as st

from studio.services.first_adventure_progress_service import (
    FirstAdventureProgressService,
)


def _step_line(done: bool, label: str, detail: str) -> str:
    icon = "✅" if done else "⬜"
    return f"{icon} **{label}** · {detail}"


def render_first_adventure_progress(ctx) -> None:
    progress = FirstAdventureProgressService(ctx.repository).status()

    with st.container(border=True):
        title_col, status_col = st.columns([3, 1])
        with title_col:
            st.markdown("### 🌟 First Adventure / 第一次完整冒险")
            st.caption(
                "Character → Baby → Dress Up → Battle → Reward → Grow Stronger"
            )
        with status_col:
            if progress.loop_complete:
                st.success("🏆 LOOP COMPLETE")
            else:
                st.info(
                    f"{progress.completed_steps}/{progress.total_steps} READY"
                )

        st.progress(
            progress.progress_fraction,
            text=f"First Play Loop · {progress.completed_steps}/{progress.total_steps}",
        )

        step_a, step_b = st.columns(2)
        with step_a:
            st.markdown(
                _step_line(
                    progress.has_character,
                    "1. Create Hero / 创造角色",
                    progress.character_name or "还没有角色",
                )
            )
            st.markdown(
                _step_line(
                    progress.has_active_baby,
                    "2. Meet Baby / 领取宝宝",
                    "Active Baby ready" if progress.has_active_baby else "还没有 Active Baby",
                )
            )
        with step_b:
            st.markdown(
                _step_line(
                    progress.gear_ready,
                    "3. Gear Up / 穿装备",
                    (
                        f"{len(progress.equipped_slots)} slots equipped"
                        if progress.gear_ready
                        else "去 Dressing Room"
                    ),
                )
            )
            st.markdown(
                _step_line(
                    progress.reward_claimed,
                    "4. Win First Drop / 赢得掉落",
                    (
                        "Bone Buckler claimed"
                        if progress.reward_claimed
                        else "Training Skeleton → Bone Buckler"
                    ),
                )
            )

        if progress.loop_complete:
            if progress.reward_equipped:
                st.success("💪 Bone Buckler 已装备。你已经完成第一次“战斗 → 掉落 → 变强”循环！")
            else:
                st.success("🎁 Bone Buckler 已经进入 Collection。第一条 Play Loop 已完成！")

        st.caption("👉 " + progress.next_hint)

        if progress.has_character:
            if st.button(
                (
                    "💪 Equip Reward & Play Again / 装上奖励再出发"
                    if progress.reward_claimed
                    else "🎮 Continue Adventure / 继续冒险"
                ),
                type="primary",
                use_container_width=True,
                key="home_continue_first_adventure",
            ):
                st.session_state.pending_app_page = "🪞 Dressing Room"
                st.rerun()
        else:
            if st.button(
                "✨ Create First Hero / 创造第一个角色",
                type="primary",
                use_container_width=True,
                key="home_create_first_hero",
            ):
                st.session_state.pending_app_page = "✨ Character Factory"
                st.rerun()
