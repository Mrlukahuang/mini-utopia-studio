from __future__ import annotations

import streamlit as st

from studio.core.enums import AssetType
from studio.services.audio_timeline_service import AudioTimelineService


def render_audio_timeline(ctx, *, episode) -> None:
    service = AudioTimelineService(ctx.repository)
    summary = service.summary(episode.episode_id)

    with st.container(border=True):
        st.markdown("#### 🎙️ Dialogue & Narration / 对白与旁白")
        a, b, c = st.columns(3)
        a.metric("Lines", summary.line_count)
        b.metric(
            "Approved",
            f"{summary.approved_count}/{summary.line_count}",
        )
        c.metric(
            "Spoken",
            f"{summary.total_spoken_seconds:.1f}s",
        )

        if summary.overlap_line_ids:
            st.warning(
                "⚠️ Timeline overlap / 时间重叠 · "
                + " · ".join(summary.overlap_line_ids)
            )

        build_label = (
            "🔄 Rebuild Baseline / 重建基础时间轨"
            if episode.audio_timeline
            else "🎙️ Build Audio Timeline / 生成对白时间轨"
        )
        if st.button(
            build_label,
            key=f"audio_build_{episode.episode_id}",
            use_container_width=True,
        ):
            service.ensure_baseline(
                episode.episode_id,
                replace=bool(episode.audio_timeline),
            )
            st.rerun()

        shot_options = [
            (scene.scene_id, shot.shot_id)
            for scene in episode.scenes
            for shot in scene.shots
        ]
        if shot_options:
            with st.expander(
                "➕ Add Narration / 添加旁白",
                expanded=False,
            ):
                selected = st.selectbox(
                    "Shot / 镜头",
                    shot_options,
                    format_func=lambda value: (
                        f"{value[0]} · {value[1]}"
                    ),
                    key=f"audio_add_shot_{episode.episode_id}",
                )
                narration = st.text_area(
                    "Narration / 旁白文字",
                    key=f"audio_add_text_{episode.episode_id}",
                    placeholder="例如：Nancy 和 Nova 第一次走进这个神秘村庄。",
                )
                if st.button(
                    "➕ Add to Timeline / 加入时间轨",
                    key=f"audio_add_{episode.episode_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        service.add_narration(
                            episode_id=episode.episode_id,
                            scene_id=selected[0],
                            shot_id=selected[1],
                            text=narration,
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        if not episode.audio_timeline:
            st.caption(
                "还没有对白时间轨。已有 Shot dialogue 或你添加旁白后，"
                "这里会出现可编辑的 timing。"
            )
            return

        character_assets = []
        for asset_id in episode.asset_ids:
            asset = ctx.repository.get_asset(asset_id)
            if asset is not None and asset.asset_type == AssetType.CHARACTER:
                character_assets.append(asset)
        character_by_id = {
            asset.asset_id: asset
            for asset in character_assets
        }

        for line in episode.audio_timeline:
            overlap = line.line_id in summary.overlap_line_ids
            label = (
                f"{'⚠️' if overlap else '🎧'} {line.line_id} · "
                f"{line.start_seconds:.1f}s–{line.end_seconds:.1f}s · "
                f"{'✅' if line.approved else '👀'}"
            )
            with st.expander(label, expanded=False):
                with st.form(
                    f"audio_line_{episode.episode_id}_{line.line_id}",
                    clear_on_submit=False,
                ):
                    speaker_kind = st.selectbox(
                        "Speaker Type / 说话者类型",
                        ["narrator", "character"],
                        index=(
                            0 if line.speaker_kind == "narrator" else 1
                        ),
                    )

                    character_ids = [
                        asset.asset_id
                        for asset in character_assets
                    ]
                    speaker_asset_id = line.speaker_asset_id
                    if speaker_kind == "character":
                        if not character_ids:
                            st.warning(
                                "这个 Episode 没有可用 Character。"
                            )
                            speaker_asset_id = None
                        else:
                            current_index = (
                                character_ids.index(line.speaker_asset_id)
                                if line.speaker_asset_id in character_ids
                                else 0
                            )
                            speaker_asset_id = st.selectbox(
                                "Character / 角色",
                                character_ids,
                                index=current_index,
                                format_func=lambda asset_id: (
                                    character_by_id[asset_id].display_name
                                ),
                            )

                    text = st.text_area(
                        "Text / 台词",
                        value=line.text,
                        height=90,
                    )
                    timing = st.columns(2)
                    start = timing[0].number_input(
                        "Start / 开始（秒）",
                        min_value=0.0,
                        value=float(line.start_seconds),
                        step=0.1,
                    )
                    duration = timing[1].number_input(
                        "Duration / 时长（秒）",
                        min_value=0.2,
                        max_value=60.0,
                        value=float(line.duration_seconds),
                        step=0.1,
                    )
                    emotion = st.text_input(
                        "Emotion / 情绪",
                        value=line.emotion,
                    )
                    delivery = st.text_input(
                        "Delivery Note / 演绎提示",
                        value=line.delivery_note,
                    )
                    approved = st.checkbox(
                        "✅ Approved / 已确认文字与时间",
                        value=line.approved,
                    )
                    save = st.form_submit_button(
                        "💾 Save Audio Line / 保存对白",
                        use_container_width=True,
                    )

                if save:
                    try:
                        service.update_line(
                            episode_id=episode.episode_id,
                            line_id=line.line_id,
                            speaker_kind=speaker_kind,
                            speaker_asset_id=speaker_asset_id,
                            text=text,
                            start_seconds=start,
                            duration_seconds=duration,
                            emotion=emotion,
                            delivery_note=delivery,
                            approved=approved,
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
