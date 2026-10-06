from __future__ import annotations

import streamlit as st

from studio.services.play_loop_service import FirstPlayLoopService


STEPS = (
    ("character_ready", "🎭 Hero", "创建一个角色"),
    ("baby_ready", "🐣 Baby", "领取 Initial Baby"),
    ("loadout_ready", "🎒 Gear", "在 Dressing Room 穿上装备"),
    ("play_session_ready", "🚪 Enter", "带这套装备进入世界"),
    ("reward_claimed", "🎁 Drop", "打败 Skeleton 并领取奖励"),
    ("reward_equipped", "🛡️ Upgrade", "装备 Bone Buckler"),
    ("stronger_session_ready", "⭐ Again", "带升级后的角色再次出发"),
)


def render_first_adventure_progress(ctx) -> None:
    service = FirstPlayLoopService(
        ctx.repository,
        equipment=ctx.equipment,
    )
    status = service.status(
        preferred_character_id=st.session_state.get("play_character_id"),
    )

    st.markdown("### 🎮 First Adventure / 第一次完整冒险")
    st.caption(
        "角色 → Baby → 换装 → 进入世界 → 战斗掉落 → 变强 → 再出发"
    )
    st.progress(
        status.completed_steps / status.total_steps,
        text=(
            f"{status.completed_steps}/{status.total_steps} · "
            + (
                "First Loop Complete! / 第一圈完成 🎉"
                if status.complete
                else "Keep going / 继续冒险"
            )
        ),
    )

    cols = st.columns(7)
    for index, (field, title, caption) in enumerate(STEPS):
        done = bool(getattr(status, field))
        with cols[index]:
            st.markdown(
                f"**{'✅' if done else '⬜'} {title}**"
            )
            st.caption(caption)

    if status.reward_waiting and not status.reward_claimed:
        st.success(
            "🎁 Skeleton 奖励正在等你！去 My Stuff 领取 Bone Buckler。"
        )

    if status.complete:
        st.success(
            "🌟 第一条 Mini Utopia 成长循环已经完成。"
            "下一次进入世界时，你会带着刚刚赢来的装备。"
        )

    target_page, label = _next_action(status)
    if st.button(
        label,
        type="primary",
        use_container_width=True,
        key="first_adventure_continue",
    ):
        st.session_state.pending_app_page = target_page
        st.rerun()


def _next_action(status):
    if not status.character_ready:
        return "✨ Character Factory", "✨ Create My Hero / 创建角色"
    if not status.baby_ready:
        return "🐣 My Baby", "🐣 Meet My Baby / 领取宝宝"
    if not status.loadout_ready:
        return "🪞 Dressing Room", "🪞 Dress My Hero / 去换装"
    if not status.play_session_ready:
        return "🪞 Dressing Room", "🎮 Play This Loadout / 带这套装备出发"
    if status.reward_waiting and not status.reward_claimed:
        return "🎒 My Stuff", "🎁 Claim Battle Reward / 领取战斗奖励"
    if not status.reward_claimed:
        return "🎮 Explore World", "💀 Fight the Skeleton / 去打 Skeleton"
    if not status.reward_equipped:
        return "🎒 My Stuff", "🛡️ Equip Bone Buckler / 装备骨盾"
    if not status.stronger_session_ready:
        return "🪞 Dressing Room", "⭐ Play Again Stronger / 带升级装备再出发"
    return "🪞 Dressing Room", "🌈 Keep Playing / 继续玩"
