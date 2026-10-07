from __future__ import annotations

import streamlit as st


def render_legacy_creator_notice(*, surface: str) -> None:
    """Explain the migration without removing access to saved Creator data."""

    st.info(
        "🚧 Creator migration / Creator 正在迁移到 Godot\n\n"
        f"当前 **{surface}** 先保留用于查看和过渡测试。"
        "新的角色创建、换装和装备编辑不会继续扩展在 Streamlit；"
        "等对应 Godot Creator 页面通过本地验收后，这里会改成只读 View "
        "+ **Open in Mini Utopia**。"
    )
