from __future__ import annotations

import streamlit as st

from studio.models.universe_memory import UniverseMemoryKind
from studio.services.living_universe_memory_service import (
    LivingUniverseMemoryService,
)


MEMORY_ICON = {
    UniverseMemoryKind.CANON_STORY: "📖",
    UniverseMemoryKind.WORLD_DISCOVERY: "🌍",
    UniverseMemoryKind.ITEM_ACQUIRED: "🎁",
    UniverseMemoryKind.BABY_MILESTONE: "🐣",
    UniverseMemoryKind.RELATIONSHIP: "💞",
    UniverseMemoryKind.PORTAL_UNLOCK: "🌀",
    UniverseMemoryKind.LORE: "✨",
}


def render_universe_memory(ctx, *, universe_id: str) -> None:
    service = LivingUniverseMemoryService(ctx.repository)
    try:
        memories = service.sync_known_state(
            universe_id=universe_id,
        )
    except NotImplementedError:
        st.caption("Living Universe Memory is unavailable for this repository.")
        return

    with st.container(border=True):
        st.markdown("### 🧠 Living Universe Memory / 宇宙记忆")
        st.caption(
            "Canon 中真正发生过的事情会留在这里。Playground 不会自动改写这份记忆。"
        )

        if not memories:
            st.info("还没有 Canon 记忆。保存第一个 Canon Story 后，这里会开始成长。")
            return

        kind_counts: dict[UniverseMemoryKind, int] = {}
        for memory in memories:
            kind_counts[memory.kind] = kind_counts.get(memory.kind, 0) + 1

        cols = st.columns(4)
        cols[0].metric(
            "📖 Stories",
            kind_counts.get(UniverseMemoryKind.CANON_STORY, 0),
        )
        cols[1].metric(
            "🌍 Worlds",
            kind_counts.get(UniverseMemoryKind.WORLD_DISCOVERY, 0),
        )
        cols[2].metric(
            "🎁 Rewards",
            kind_counts.get(UniverseMemoryKind.ITEM_ACQUIRED, 0),
        )
        cols[3].metric(
            "🐣 Baby",
            kind_counts.get(UniverseMemoryKind.BABY_MILESTONE, 0),
        )

        st.markdown("#### Recent Canon Memory / 最近记忆")
        for memory in memories[:8]:
            icon = MEMORY_ICON.get(memory.kind, "✨")
            st.markdown(f"{icon} **{memory.kind.value.replace('_', ' ').title()}**")
            st.caption(memory.summary)
