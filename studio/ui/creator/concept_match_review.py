from __future__ import annotations

from html import escape

import streamlit as st
import streamlit.components.v1 as components

from studio.models.world import WorldBlueprint


_KIND_EMOJI = {
    "portal": "🌀",
    "water": "💧",
    "bridge": "🌉",
    "structure": "🏰",
    "landmark": "⭐",
    "terrain": "🏝️",
    "decoration": "✨",
}


def _layout_svg(blueprint: WorldBlueprint) -> str:
    width = 420
    height = 420
    pad = 24
    grid_w = blueprint.grid.width or 50
    grid_d = blueprint.grid.depth or 50

    def sx(x: float) -> float:
        return pad + (x / grid_w) * (width - pad * 2)

    def sy(z: float) -> float:
        return height - pad - (z / grid_d) * (height - pad * 2)

    parts = [
        f'<svg width="100%" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Blueprint top-down map">',
        '<rect x="1" y="1" width="418" height="418" rx="24" fill="#FFFDF8" stroke="#E9E2F3"/>',
    ]

    for i in range(1, 5):
        x = pad + (width - pad * 2) * i / 5
        z = pad + (height - pad * 2) * i / 5
        parts.append(f'<line x1="{x}" y1="{pad}" x2="{x}" y2="{height-pad}" stroke="#EEEAF5" stroke-width="1"/>')
        parts.append(f'<line x1="{pad}" y1="{z}" x2="{width-pad}" y2="{z}" stroke="#EEEAF5" stroke-width="1"/>')

    for path in blueprint.paths[:1]:
        if len(path.points) > 1:
            points = " ".join(f"{sx(p.x)},{sy(p.z)}" for p in path.points)
            parts.append(
                f'<polyline points="{points}" fill="none" stroke="#D8B9E8" '
                f'stroke-width="{max(3, path.width_cells * 1.4)}" stroke-linecap="round" '
                'stroke-linejoin="round" opacity=".78"/>'
            )

    for element in blueprint.layout_elements:
        x = sx(element.position.x)
        y = sy(element.position.z)
        w = max(18, element.width / grid_w * (width - pad * 2))
        d = max(18, element.depth / grid_d * (height - pad * 2))
        if element.kind == "water":
            parts.append(
                f'<ellipse cx="{x}" cy="{y}" rx="{w/2}" ry="{d/2}" '
                'fill="#CDECF7" stroke="#8EC9DE" stroke-width="2" opacity=".82"/>'
            )
        else:
            parts.append(
                f'<rect x="{x-w/2}" y="{y-d/2}" width="{w}" height="{d}" rx="9" '
                'fill="#F4E7FA" stroke="#BFA7D8" stroke-width="2"/>'
            )
        emoji = _KIND_EMOJI.get(element.kind, "•")
        label = escape(element.name[:20])
        parts.append(
            f'<text x="{x}" y="{y-3}" text-anchor="middle" font-size="18">{emoji}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y+15}" text-anchor="middle" font-size="8" '
            f'font-family="sans-serif" fill="#403A56">{label}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def render_concept_match_review(ctx, *, asset, studio_mode: bool) -> None:
    raw_blueprint = asset.metadata.get("world_blueprint")
    concept_path = asset.metadata.get("world_concept_path")
    if not raw_blueprint or not concept_path:
        return

    blueprint = WorldBlueprint.model_validate(raw_blueprint)
    if not blueprint.layout_elements:
        return

    reviewed = bool(asset.metadata.get("world_concept_match_reviewed"))
    title = "✅ Concept Match Reviewed" if reviewed else "🎯 Concept Match Review"
    with st.expander(title, expanded=not reviewed):
        st.caption(
            "把 Concept 和可玩布局放在一起看。觉得某个元素位置或大小不对，"
            "直接轻轻调整，不需要重新生成图片。"
        )

        concept_col, map_col = st.columns(2, gap="large")
        with concept_col:
            try:
                st.image(
                    ctx.storage.get_bytes(concept_path),
                    caption="Approved Concept / 已选概念图",
                    use_container_width=True,
                )
            except Exception:
                st.info("Concept preview 暂时无法读取。")

        with map_col:
            st.markdown("**Playable Layout / 可玩布局俯视图**")
            components.html(_layout_svg(blueprint), height=430, scrolling=False)

        element = st.selectbox(
            "What do you want to adjust? / 想调整什么？",
            blueprint.layout_elements,
            format_func=lambda item: f"{_KIND_EMOJI.get(item.kind, '•')} {item.name}",
            key=f"concept_match_element_{asset.asset_id}",
        )

        if studio_mode:
            st.caption(
                f"Studio · {element.element_id} · {element.kind} · "
                f"x={element.position.x:.1f}, z={element.position.z:.1f} · "
                f"{element.width:.1f}×{element.depth:.1f}"
            )

        left, right, forward, back = st.columns(4)
        if left.button("← Left / 左", key=f"cm_left_{asset.asset_id}", use_container_width=True):
            ctx.world_concept_match.apply_correction(
                location_asset_id=asset.asset_id,
                element_id=element.element_id,
                action="left",
            )
            st.rerun()
        if right.button("Right / 右 →", key=f"cm_right_{asset.asset_id}", use_container_width=True):
            ctx.world_concept_match.apply_correction(
                location_asset_id=asset.asset_id,
                element_id=element.element_id,
                action="right",
            )
            st.rerun()
        if forward.button("↑ Forward / 前", key=f"cm_forward_{asset.asset_id}", use_container_width=True):
            ctx.world_concept_match.apply_correction(
                location_asset_id=asset.asset_id,
                element_id=element.element_id,
                action="forward",
            )
            st.rerun()
        if back.button("↓ Back / 后", key=f"cm_back_{asset.asset_id}", use_container_width=True):
            ctx.world_concept_match.apply_correction(
                location_asset_id=asset.asset_id,
                element_id=element.element_id,
                action="back",
            )
            st.rerun()

        smaller, bigger, spacer, approve = st.columns([1, 1, .25, 1.7])
        if smaller.button("➖ Smaller / 小一点", key=f"cm_smaller_{asset.asset_id}", use_container_width=True):
            ctx.world_concept_match.apply_correction(
                location_asset_id=asset.asset_id,
                element_id=element.element_id,
                action="smaller",
            )
            st.rerun()
        if bigger.button("➕ Bigger / 大一点", key=f"cm_bigger_{asset.asset_id}", use_container_width=True):
            ctx.world_concept_match.apply_correction(
                location_asset_id=asset.asset_id,
                element_id=element.element_id,
                action="bigger",
            )
            st.rerun()
        with approve:
            if st.button(
                "💖 Looks Good / 就这样",
                type="primary",
                key=f"cm_reviewed_{asset.asset_id}",
                use_container_width=True,
            ):
                ctx.world_concept_match.mark_reviewed(location_asset_id=asset.asset_id)
                st.rerun()

        history = asset.metadata.get("world_concept_match_history", [])
        if studio_mode and history:
            st.caption(f"Studio · Human corrections saved: {len(history)}")
