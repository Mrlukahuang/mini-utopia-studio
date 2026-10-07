from __future__ import annotations

import streamlit as st

from studio.services.baby_service import BABY_ARCHETYPES, BABY_XP_PER_LEVEL, BabyService
from studio.services.quest_reward_service import QuestRewardService
from studio.ui.theme import render_game_hero


BABY_VISUALS = {
    "cloud_baby": ("☁️🐣", "Soft clouds · curious little floater"),
    "sheep_baby": ("🐑✨", "Fluffy wool · gentle little explorer"),
    "star_baby": ("🌟🐣", "Tiny starlight · bright little dreamer"),
    "robot_baby": ("🤖💫", "Toy robot · clever little helper"),
    "forest_baby": ("🌱🦊", "Leafy forest spirit · brave little scout"),
}


def _render_baby_preview(baby) -> None:
    emoji, subtitle = BABY_VISUALS.get(baby.species_id, ("🐣✨", "Mini Utopia Baby"))
    st.markdown(
        f"""
        <div style="
            min-height:320px;
            border-radius:28px;
            border:1px solid rgba(255,255,255,.12);
            display:flex;
            align-items:center;
            justify-content:center;
            flex-direction:column;
            gap:10px;
            background:linear-gradient(145deg, rgba(255,255,255,.07), rgba(255,255,255,.025));
        ">
            <div style="font-size:92px; line-height:1">{emoji}</div>
            <div style="font-size:26px; font-weight:800">{baby.display_name}</div>
            <div style="opacity:.7">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_my_baby(ctx) -> None:
    render_game_hero(
        "My Baby 🐣✨",
        "这是会一直陪你长大的 Initial Baby。名字、成长和羁绊都会保存下来。",
        kicker="COMPANION · GROW · BOND",
    )

    babies = BabyService(ctx.repository)
    growth_rewards = QuestRewardService(
        ctx.repository,
        equipment=ctx.equipment,
        babies=babies,
    ).claim_baby_growth()
    for reward in growth_rewards:
        reward_label = (
            "✨ XP"
            if reward.reward_type.value == "baby_xp"
            else "💞 Bond"
        )
        st.success(
            f"🌱 Quest Growth · {reward.baby_name} · "
            f"{reward_label} +{reward.amount} · Lv.{reward.level}"
        )

    roster = babies.get_roster()

    if not roster.babies:
        st.markdown("### Meet Your Initial Baby / 选择你的第一个宝宝")
        st.caption("BB-01 先建立永久身份与成长基础；战斗、繁殖和完整进化以后再做。")

        left, right = st.columns([1.15, 1], gap="large")
        with left:
            species_id = st.selectbox(
                "Baby Archetype / 宝宝类型",
                list(BABY_ARCHETYPES),
                format_func=lambda value: BABY_ARCHETYPES[value],
                key="initial_baby_species",
            )
            display_name = st.text_input(
                "Baby Name / 宝宝名字",
                value="My Baby",
                max_chars=40,
                key="initial_baby_name",
            )
            if st.button(
                "🐣 Meet My Baby / 领取宝宝",
                type="primary",
                use_container_width=True,
            ):
                try:
                    babies.create_initial_baby(
                        display_name=display_name,
                        species_id=species_id,
                    )
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        with right:
            emoji, subtitle = BABY_VISUALS.get(species_id, ("🐣✨", "Mini Utopia Baby"))
            st.markdown(
                f"""
                <div style="min-height:300px;border-radius:28px;border:1px solid rgba(255,255,255,.12);
                display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;">
                    <div style="font-size:92px">{emoji}</div>
                    <div style="font-size:22px;font-weight:800">{BABY_ARCHETYPES[species_id]}</div>
                    <div style="opacity:.7">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    active = roster.active_baby() or roster.babies[0]

    preview_col, info_col = st.columns([1.05, 1.15], gap="large")
    with preview_col:
        _render_baby_preview(active)
        st.caption(
            "Procedural preview for BB-01 · later this same Baby identity plugs into the Godot follow runtime."
        )

    with info_col:
        st.markdown(f"### 🐣 {active.display_name}")
        st.caption(BABY_ARCHETYPES.get(active.species_id, active.species_id))

        a, b, c = st.columns(3)
        a.metric("⭐ Level", active.level)
        b.metric("✨ XP", active.xp)
        c.metric("💞 Bond", active.bond)

        level_progress = (active.xp % BABY_XP_PER_LEVEL) / BABY_XP_PER_LEVEL
        st.progress(
            level_progress,
            text=f"Next level · {active.xp % BABY_XP_PER_LEVEL}/{BABY_XP_PER_LEVEL} XP",
        )

        new_name = st.text_input(
            "Rename Baby / 改名字",
            value=active.display_name,
            max_chars=40,
            key=f"rename_baby_{active.baby_id}",
        )
        rename_col, active_col = st.columns(2)
        with rename_col:
            if st.button(
                "💾 Save Name",
                key=f"save_baby_name_{active.baby_id}",
                use_container_width=True,
            ):
                try:
                    babies.rename(baby_id=active.baby_id, display_name=new_name)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        with active_col:
            st.button(
                "✅ Active Baby",
                key=f"baby_active_{active.baby_id}",
                disabled=True,
                use_container_width=True,
            )

        st.markdown("#### How Baby Grows / 怎么长大")
        st.info(
            "一起完成 Quest、探索世界，会获得 XP 和 Bond。"
            " 成长会自动保存，不需要手动加点。"
        )

        with st.expander("Baby Identity / 永久身份", expanded=False):
            st.code(
                f"baby_id: {active.baby_id}\n"
                f"appearance_seed: {active.appearance_seed}\n"
                f"growth_stage: {active.growth_stage.value}\n"
                f"species_id: {active.species_id}",
                language="text",
            )

    if len(roster.babies) > 1:
        st.divider()
        st.markdown("### My Babies / 我的宝宝")
        for baby in roster.babies:
            cols = st.columns([4, 1])
            cols[0].write(
                f"🐣 **{baby.display_name}** · "
                f"{BABY_ARCHETYPES.get(baby.species_id, baby.species_id)} · Lv.{baby.level}"
            )
            if baby.baby_id == roster.active_baby_id:
                cols[1].caption("Active")
            elif cols[1].button("Set Active", key=f"set_active_{baby.baby_id}"):
                babies.set_active(baby_id=baby.baby_id)
                st.rerun()
