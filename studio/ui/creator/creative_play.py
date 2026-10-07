from __future__ import annotations

import streamlit as st

from studio.models.world_creative import (
    CREATIVE_PROP_LABELS,
    CreativePropType,
    WorldCreativeLayout,
)
from studio.services.world_creative_layout_service import WorldCreativeLayoutService


PLACEMENT_ZONES = {
    "🏡 Near Spawn / 出生点附近": (25.0, 0.0, 27.0),
    "🌼 Left Garden / 左边花园": (18.0, 0.0, 24.0),
    "⭐ Right Garden / 右边花园": (32.0, 0.0, 24.0),
    "🌀 Portal Path / 传送门小路": (25.0, 0.0, 35.0),
}


def render_creative_play(ctx, *, world_asset_id: str) -> WorldCreativeLayout:
    service = WorldCreativeLayoutService(ctx.repository)
    layout = service.get_layout(world_asset_id)

    with st.expander(
        f"🎨 Creative Play / 装饰我的世界 · {len(layout.decorations)} items",
        expanded=False,
    ):
        st.caption(
            "装饰只是你的 Creative Layout，不会修改 World Blueprint、Quest 或 Story。"
        )

        prop = st.selectbox(
            "Choose Prop / 选择装饰",
            list(CreativePropType),
            format_func=lambda value: CREATIVE_PROP_LABELS[value],
            key=f"creative_prop_{world_asset_id}",
        )
        zone = st.selectbox(
            "Placement Zone / 放置区域",
            list(PLACEMENT_ZONES),
            key=f"creative_zone_{world_asset_id}",
        )
        base_x, base_y, base_z = PLACEMENT_ZONES[zone]

        x_col, z_col = st.columns(2)
        with x_col:
            x_offset = st.slider(
                "↔ X",
                -6.0,
                6.0,
                0.0,
                0.5,
                key=f"creative_x_{world_asset_id}",
            )
        with z_col:
            z_offset = st.slider(
                "↕ Z",
                -6.0,
                6.0,
                0.0,
                0.5,
                key=f"creative_z_{world_asset_id}",
            )
        rot_col, scale_col = st.columns(2)
        with rot_col:
            rotation = st.slider(
                "Rotate / 旋转",
                0,
                315,
                0,
                45,
                key=f"creative_rot_{world_asset_id}",
            )
        with scale_col:
            scale = st.slider(
                "Size / 大小",
                0.5,
                2.0,
                1.0,
                0.1,
                key=f"creative_scale_{world_asset_id}",
            )

        if st.button(
            "✨ Place Decoration / 放进去",
            type="primary",
            use_container_width=True,
            key=f"creative_place_{world_asset_id}",
        ):
            service.place(
                world_asset_id=world_asset_id,
                prop_type=prop,
                position=(base_x + x_offset, base_y, base_z + z_offset),
                rotation_y=float(rotation),
                scale=float(scale),
            )
            st.rerun()

        layout = service.get_layout(world_asset_id)
        if layout.decorations:
            st.markdown("#### Saved Decorations / 已保存装饰")
            for item in layout.decorations:
                row, action = st.columns([4, 1])
                with row:
                    st.write(
                        f"{item.display_name} · "
                        f"({item.position[0]:.1f}, {item.position[2]:.1f}) · "
                        f"{item.rotation_y:.0f}° · {item.scale:.1f}×"
                    )
                with action:
                    if st.button(
                        "Remove",
                        key=f"remove_decor_{item.decoration_id}",
                        use_container_width=True,
                    ):
                        service.remove(
                            world_asset_id=world_asset_id,
                            decoration_id=item.decoration_id,
                        )
                        st.rerun()

            confirm_key = f"confirm_clear_creative_{world_asset_id}"
            if not st.session_state.get(confirm_key):
                if st.button(
                    "🧹 Clear My Layout / 清空我的装饰",
                    key=f"ask_clear_creative_{world_asset_id}",
                ):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning("只会清空 Creative Layout，不会删除 World。")
                yes, no = st.columns(2)
                with yes:
                    if st.button(
                        "Yes, clear / 确认清空",
                        type="primary",
                        key=f"clear_creative_{world_asset_id}",
                        use_container_width=True,
                    ):
                        service.clear(world_asset_id)
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with no:
                    if st.button(
                        "Cancel / 取消",
                        key=f"cancel_clear_creative_{world_asset_id}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
        else:
            st.info("还没有装饰。放一个 Star Lamp 试试看 ✨")

    return service.get_layout(world_asset_id)
