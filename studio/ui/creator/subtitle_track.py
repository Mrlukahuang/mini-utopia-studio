from __future__ import annotations

import streamlit as st

from studio.services.subtitle_track_service import SubtitleTrackService


def render_subtitle_track(ctx, *, episode) -> None:
    service = SubtitleTrackService(ctx.repository)
    summary = service.summary(episode.episode_id)

    with st.container(border=True):
        st.markdown("#### 💬 Subtitle Track / 字幕轨")
        a, b, c = st.columns(3)
        a.metric("Cues", summary.cue_count)
        b.metric(
            "Approved",
            f"{summary.approved_count}/{summary.cue_count}",
        )
        c.metric("Stale", summary.stale_count)

        if not episode.audio_timeline:
            st.caption(
                "先在上面的 Dialogue & Narration 时间轨添加对白或旁白，"
                "字幕会从正式音频时间生成。"
            )
            return

        generate_label = (
            "🔄 Sync Subtitles / 同步字幕"
            if episode.subtitle_track
            else "💬 Generate Subtitles / 生成字幕"
        )
        if st.button(
            generate_label,
            key=f"subtitle_generate_{episode.episode_id}",
            type="primary" if not episode.subtitle_track else "secondary",
            use_container_width=True,
        ):
            service.ensure_track(
                episode.episode_id,
                replace_stale=False,
            )
            st.rerun()

        if not episode.subtitle_track:
            return

        for cue in episode.subtitle_track:
            status = service.status_for(
                episode_id=episode.episode_id,
                cue=cue,
            )
            icon = "✅" if status == "ready" else "🟠"
            with st.expander(
                (
                    f"{icon} {cue.cue_id} · "
                    f"{cue.start_seconds:.1f}s–{cue.end_seconds:.1f}s · "
                    f"{'Approved' if cue.approved and status == 'ready' else 'Review'}"
                ),
                expanded=False,
            ):
                if status == "stale":
                    st.warning(
                        "源对白已经变化，这条字幕已过期。"
                        "刷新只会更新字幕，不会改写对白。"
                    )
                    if st.button(
                        "🔄 Refresh from Audio / 从对白刷新",
                        key=f"subtitle_refresh_{episode.episode_id}_{cue.cue_id}",
                        use_container_width=True,
                    ):
                        service.refresh_cue(
                            episode_id=episode.episode_id,
                            cue_id=cue.cue_id,
                        )
                        st.rerun()

                with st.form(
                    f"subtitle_form_{episode.episode_id}_{cue.cue_id}",
                    clear_on_submit=False,
                ):
                    speaker_label = st.text_input(
                        "Speaker Label / 角色标签",
                        value=cue.speaker_label,
                    )
                    text = st.text_area(
                        "Subtitle / 字幕",
                        value=cue.text,
                        height=80,
                    )
                    timing = st.columns(2)
                    start = timing[0].number_input(
                        "Start / 开始（秒）",
                        min_value=0.0,
                        value=float(cue.start_seconds),
                        step=0.1,
                    )
                    end = timing[1].number_input(
                        "End / 结束（秒）",
                        min_value=0.1,
                        value=float(cue.end_seconds),
                        step=0.1,
                    )
                    approved = st.checkbox(
                        "✅ Approved / 字幕已确认",
                        value=cue.approved,
                        disabled=status == "stale",
                    )
                    save = st.form_submit_button(
                        "💾 Save Subtitle / 保存字幕",
                        use_container_width=True,
                        disabled=status == "stale",
                    )

                if save:
                    try:
                        service.update_cue(
                            episode_id=episode.episode_id,
                            cue_id=cue.cue_id,
                            start_seconds=start,
                            end_seconds=end,
                            text=text,
                            speaker_label=speaker_label,
                            approved=approved,
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        srt = service.srt_text(episode.episode_id)
        if srt:
            with st.expander("📄 SRT Preview / 字幕文件预览"):
                st.code(srt, language="text")
                st.download_button(
                    "⬇️ Download SRT / 下载字幕",
                    data=srt.encode("utf-8"),
                    file_name=f"{episode.episode_id}.srt",
                    mime="application/x-subrip",
                    key=f"subtitle_download_{episode.episode_id}",
                    use_container_width=True,
                )
