from __future__ import annotations

import streamlit as st

from studio.models.episode import (
    PerformanceCue,
    ShotBlockingPoint,
    ShotBlockingSpec,
    ShotCameraMotionSpec,
)
from studio.services.baby_service import BabyService
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)
from studio.services.episode_batch_render_service import (
    EpisodeBatchRenderService,
)
from studio.services.episode_assembly_service import (
    EpisodeAssemblyService,
)
from studio.services.episode_service import EpisodeService
from studio.services.production_status_service import (
    EpisodeProductionStatusService,
)
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.storyboard_service import StoryboardService
from studio.services.shot_render_service import ShotRenderService
from studio.ui.creator.audio_timeline import render_audio_timeline
from studio.ui.creator.subtitle_track import render_subtitle_track


def render_episode_library(ctx) -> None:
    st.header("🎬 Episodes / 剧集")
    st.write(
        "Episode 是把 Story 变成可以继续拆 Scene、Shot、Camera 的制作容器。"
        " 它继续引用同一批角色、世界和道具，不复制资产。"
    )

    episode_service = EpisodeService(ctx.repository)
    scene_service = SceneBreakdownService(ctx.repository)
    shot_service = ShotPlanService(ctx.repository)
    director_service = DirectorShotSessionService(
        ctx.repository,
        ctx.character_runtime,
        equipment=ctx.equipment,
        babies=BabyService(ctx.repository),
    )
    storyboard_service = StoryboardService(
        ctx.repository,
        director_service,
    )
    shot_render_service = ShotRenderService(
        ctx.repository,
        director_service,
        storyboard_service,
    )
    batch_render_service = EpisodeBatchRenderService(
        ctx.repository,
        storyboard_service,
        shot_render_service,
    )
    episode_assembly_service = EpisodeAssemblyService(
        ctx.repository,
        shot_render_service,
    )
    production_status_service = EpisodeProductionStatusService(
        ctx.repository,
        storyboard_service,
        shot_renderer=shot_render_service,
    )
    episodes = episode_service.list_episodes()
    episodes = [
        shot_service.ensure_blocking(episode.episode_id)
        if any(
            shot.blocking is None
            for scene in episode.scenes
            for shot in scene.shots
        )
        else episode
        for episode in episodes
    ]
    episodes = [
        shot_service.ensure_camera_motion(episode.episode_id)
        if any(
            shot.camera_motion is None
            for scene in episode.scenes
            for shot in scene.shots
        )
        else episode
        for episode in episodes
    ]
    episodes = [
        shot_service.ensure_performance_cues(episode.episode_id)
        if any(
            shot.performance_cues is None
            for scene in episode.scenes
            for shot in scene.shots
        )
        else episode
        for episode in episodes
    ]
    if not episodes:
        st.info("还没有 Episode。去 Stories 选择一个故事，点击 Create Episode。")
        return

    for episode in episodes:
        story = ctx.repository.get_story(episode.story_id)
        with st.container(border=True):
            head, stats = st.columns([3, 1])
            with head:
                st.markdown(f"### 🎬 {episode.title}")
                st.caption(
                    f"{episode.episode_id} · "
                    f"{episode.mode.value.title()} · "
                    f"Story {episode.story_id}"
                )
                if story is not None:
                    st.write(story.premise)
            with stats:
                st.metric("Scenes", len(episode.scenes))
                shot_count = sum(
                    len(scene.shots) for scene in episode.scenes
                )
                st.metric("Shots", shot_count)
                st.metric(
                    "Duration",
                    f"{shot_service.total_duration(episode):.1f}s",
                )

            st.caption(
                "🌍 World · "
                + (episode.world_asset_id or "—")
                + " · 🐣 Baby · "
                + (episode.active_baby_id or "—")
                + " · 🧠 Memory refs · "
                + str(len(episode.continuity_memory_ids))
            )

            action_left, action_right = st.columns(2)
            with action_left:
                if not episode.scenes:
                    if st.button(
                        "📝 Build Script & Scenes / 拆成场景",
                        key=f"build_scenes_{episode.episode_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        scene_service.build_from_story(episode.episode_id)
                        st.rerun()
                else:
                    st.caption(
                        "Scene breakdown 已保存。下面可以逐场编辑。"
                    )
            with action_right:
                if episode.scenes:
                    confirm_key = f"confirm_rebuild_scenes_{episode.episode_id}"
                    if not st.session_state.get(confirm_key):
                        if st.button(
                            "🔄 Rebuild from Story / 按故事重建",
                            key=f"ask_rebuild_scenes_{episode.episode_id}",
                            use_container_width=True,
                        ):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        st.warning("重建会覆盖 Scene 文本编辑，但不会改 Story。")
                        yes, no = st.columns(2)
                        with yes:
                            if st.button(
                                "Confirm",
                                key=f"confirm_rebuild_{episode.episode_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                scene_service.build_from_story(
                                    episode.episode_id,
                                    replace=True,
                                )
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
                        with no:
                            if st.button(
                                "Cancel",
                                key=f"cancel_rebuild_{episode.episode_id}",
                                use_container_width=True,
                            ):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()

            if episode.scenes:
                shot_count = sum(
                    len(scene.shots) for scene in episode.scenes
                )
                if shot_count == 0:
                    if st.button(
                        "🎥 Build Shot List / 生成镜头表",
                        key=f"build_shots_{episode.episode_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        shot_service.build_for_episode(episode.episode_id)
                        st.rerun()
                else:
                    confirm_shots_key = (
                        f"confirm_rebuild_shots_{episode.episode_id}"
                    )
                    if not st.session_state.get(confirm_shots_key):
                        if st.button(
                            "🎥 Rebuild Shot List / 重建镜头表",
                            key=f"ask_rebuild_shots_{episode.episode_id}",
                            use_container_width=True,
                        ):
                            st.session_state[confirm_shots_key] = True
                            st.rerun()
                    else:
                        st.warning(
                            "重建会覆盖 Shot 编辑，但不会修改 Scene 或 Story。"
                        )
                        yes_shot, no_shot = st.columns(2)
                        with yes_shot:
                            if st.button(
                                "Confirm Shot Rebuild",
                                key=f"confirm_shots_{episode.episode_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                shot_service.build_for_episode(
                                    episode.episode_id,
                                    replace=True,
                                )
                                st.session_state.pop(
                                    confirm_shots_key,
                                    None,
                                )
                                st.rerun()
                        with no_shot:
                            if st.button(
                                "Cancel",
                                key=f"cancel_shots_{episode.episode_id}",
                                use_container_width=True,
                            ):
                                st.session_state.pop(
                                    confirm_shots_key,
                                    None,
                                )
                                st.rerun()

                production = production_status_service.status(
                    episode.episode_id
                )
                with st.container(border=True):
                    st.markdown("#### 🎬 Production Progress / 制作进度")
                    st.progress(
                        production.progress_percent / 100,
                        text=f"{production.progress_percent}% · "
                        "Story → Scene → Shot → Storyboard → Render",
                    )
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric(
                        "Scenes",
                        f"{production.scenes_ready}/{production.scenes_total}",
                    )
                    p2.metric(
                        "Shots",
                        f"{production.shots_ready}/{production.shots_total}",
                    )
                    p3.metric(
                        "Storyboard",
                        f"{production.storyboard_ready}/{production.storyboard_total}",
                    )
                    p4.metric(
                        "Approved",
                        f"{production.storyboard_approved}/{production.storyboard_total}",
                    )

                    next_labels = {
                        "build_scenes": "📝 Build Scenes / 拆场景",
                        "build_shots": "🎥 Build Shot List / 生成镜头",
                        "generate_storyboard": "🖼️ Generate Next Frame / 生成下一张分镜",
                        "review_storyboard": "👀 Review Storyboard Below / 审核下方分镜",
                        "render_shots": "🎬 Storyboard Approved · Ready to Render",
                        "assemble_episode": "✂️ Shots Rendered · Ready to Assemble",
                        "complete": "✅ Episode Complete / 剧集完成",
                    }
                    next_label = next_labels[production.next_action]

                    if production.next_action == "build_scenes":
                        if st.button(
                            next_label,
                            key=f"production_next_scenes_{episode.episode_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            scene_service.build_from_story(
                                episode.episode_id
                            )
                            st.rerun()
                    elif production.next_action == "build_shots":
                        if st.button(
                            next_label,
                            key=f"production_next_shots_{episode.episode_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            shot_service.build_for_episode(
                                episode.episode_id
                            )
                            st.rerun()
                    elif production.next_action == "generate_storyboard":
                        if st.button(
                            next_label,
                            key=f"production_next_storyboard_{episode.episode_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            for production_scene in episode.scenes:
                                generated_one = False
                                for production_shot in production_scene.shots:
                                    frame = storyboard_service.status_for(
                                        episode_id=episode.episode_id,
                                        scene_id=production_scene.scene_id,
                                        shot_id=production_shot.shot_id,
                                    )
                                    if frame.status != "ready":
                                        with st.spinner(
                                            "🎬 正在生成下一张 Storyboard…"
                                        ):
                                            storyboard_service.generate_frame(
                                                episode_id=episode.episode_id,
                                                scene_id=production_scene.scene_id,
                                                shot_id=production_shot.shot_id,
                                            )
                                        generated_one = True
                                        break
                                if generated_one:
                                    break
                            st.rerun()
                    elif production.next_action == "review_storyboard":
                        st.info(
                            next_label
                            + " · "
                            + f"{production.storyboard_needs_change} 需修改 · "
                            + f"{production.storyboard_stale} 已过期"
                        )
                    elif production.next_action == "render_shots":
                        st.success(next_label)
                        if st.button(
                            "🎬 Render Approved Episode / 批量渲染已批准镜头",
                            key=f"batch_render_{episode.episode_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            with st.spinner(
                                "🎬 正在逐镜头渲染；已完成镜头不会重复渲染…"
                            ):
                                batch_result = (
                                    batch_render_service.render_episode(
                                        episode.episode_id
                                    )
                                )
                            if batch_result.failed_shots:
                                st.warning(
                                    "部分镜头失败，可单独或再次批量重试："
                                    + ", ".join(batch_result.failed_shots)
                                )
                            if batch_result.blocked_shots:
                                st.info(
                                    "这些镜头尚未批准 Storyboard，已安全跳过："
                                    + ", ".join(batch_result.blocked_shots)
                                )
                            if (
                                batch_result.rendered_now
                                or batch_result.already_rendered
                            ):
                                st.success(
                                    "Episode render · "
                                    f"新渲染 {batch_result.rendered_now} · "
                                    f"已存在 {batch_result.already_rendered}"
                                )
                            st.rerun()
                    elif production.next_action == "assemble_episode":
                        st.success(next_label)
                        assembly_status = episode_assembly_service.status_for(
                            episode.episode_id
                        )
                        if assembly_status.status in {
                            "missing",
                            "stale",
                            "failed",
                        }:
                            if st.button(
                                "✂️ Assemble Episode / 拼接剧集",
                                key=f"assemble_episode_{episode.episode_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                with st.spinner(
                                    "✂️ 正在按 Shot 顺序拼接 Episode…"
                                ):
                                    assembled = episode_assembly_service.assemble(
                                        episode.episode_id
                                    )
                                if assembled.status == "ready":
                                    st.rerun()
                                else:
                                    st.warning(
                                        "Episode 拼接暂未完成："
                                        + assembled.error
                                    )
                    else:
                        st.success(next_label)

                assembly_status = episode_assembly_service.status_for(
                    episode.episode_id
                )
                if assembly_status.status in {"ready", "stale", "failed"}:
                    with st.container(border=True):
                        st.markdown("#### ✂️ Episode Assembly / 剧集成片")
                        badge = {
                            "ready": "✅ Ready / 已拼接",
                            "stale": "🟠 Stale / 需要重新拼接",
                            "failed": "⚠️ Failed / 拼接失败",
                        }.get(
                            assembly_status.status,
                            assembly_status.status,
                        )
                        st.caption(
                            f"{badge} · {assembly_status.clip_count} clips · "
                            f"{assembly_status.total_duration_seconds:.1f}s"
                        )
                        assembled_video = (
                            episode_assembly_service.video_bytes(
                                assembly_status
                            )
                        )
                        if assembled_video is not None:
                            st.video(assembled_video)
                            st.download_button(
                                "⬇️ Download Episode MP4 / 下载剧集",
                                data=assembled_video,
                                file_name=f"{episode.episode_id}.mp4",
                                mime="video/mp4",
                                key=f"download_episode_{episode.episode_id}",
                                use_container_width=True,
                            )
                        if assembly_status.status == "stale":
                            st.info(
                                "Shot 或批准状态有变化；原视频保留，"
                                "重新拼接后才会成为当前版本。"
                            )

                render_audio_timeline(
                    ctx,
                    episode=episode,
                )

                render_subtitle_track(
                    ctx,
                    episode=episode,
                )

                st.markdown("#### 🖼️ Storyboard / 分镜板")
                storyboard_rows = [
                    (scene, shot)
                    for scene in episode.scenes
                    for shot in scene.shots
                ]
                frame_states = []
                for storyboard_scene, storyboard_shot in storyboard_rows:
                    try:
                        frame_states.append(
                            storyboard_service.status_for(
                                episode_id=episode.episode_id,
                                scene_id=storyboard_scene.scene_id,
                                shot_id=storyboard_shot.shot_id,
                            )
                        )
                    except ValueError:
                        continue

                ready_count = sum(
                    frame.status == "ready"
                    for frame in frame_states
                )
                approved_count = sum(
                    frame.approved_current
                    for frame in frame_states
                )
                needs_change_count = sum(
                    frame.status == "ready"
                    and frame.review_status == "needs_change"
                    and frame.review_source_fingerprint
                    == frame.source_fingerprint
                    for frame in frame_states
                )
                stale_count = sum(
                    frame.status == "stale"
                    for frame in frame_states
                )
                summary_cols = st.columns(4)
                summary_cols[0].metric(
                    "Storyboard",
                    f"{ready_count}/{len(storyboard_rows)}",
                )
                summary_cols[1].metric(
                    "Approved",
                    f"{approved_count}/{len(storyboard_rows)}",
                )
                summary_cols[2].metric(
                    "Needs Change",
                    needs_change_count,
                )
                summary_cols[3].metric("Stale", stale_count)

                status_icon = {
                    "ready": "✅",
                    "missing": "⬜",
                    "stale": "🟠",
                    "failed": "⚠️",
                }
                storyboard_cols = st.columns(3)
                for frame_index, (
                    storyboard_scene,
                    storyboard_shot,
                ) in enumerate(storyboard_rows):
                    frame = storyboard_service.status_for(
                        episode_id=episode.episode_id,
                        scene_id=storyboard_scene.scene_id,
                        shot_id=storyboard_shot.shot_id,
                    )
                    with storyboard_cols[frame_index % 3]:
                        with st.container(border=True):
                            st.markdown(
                                f"**{status_icon.get(frame.status, '⬜')} "
                                f"{storyboard_shot.shot_id}**"
                            )
                            st.caption(
                                f"{storyboard_scene.story_beat or 'SCENE'} · "
                                f"{frame.capture_time_seconds:.1f}s · "
                                f"{frame.camera_summary}"
                            )
                            image_bytes = storyboard_service.frame_bytes(
                                frame
                            )
                            if image_bytes is not None:
                                st.image(
                                    image_bytes,
                                    caption=(
                                        f"{frame.blocking_summary} · "
                                        f"{frame.status.title()}"
                                    ),
                                    use_container_width=True,
                                )
                            else:
                                st.caption(
                                    "Planning frame not generated yet / "
                                    "分镜画面还没生成"
                                )

                            review_badge = {
                                "approved": "✅ Approved / 已批准",
                                "needs_change": "📝 Needs Change / 需修改",
                                "unreviewed": "👀 Unreviewed / 待审核",
                            }.get(
                                frame.review_status,
                                "👀 Unreviewed / 待审核",
                            )
                            if frame.status == "stale":
                                review_badge += " · ⚠️ Stale"
                            st.caption(review_badge)

                            if frame.review_note:
                                st.caption(
                                    "💬 " + frame.review_note
                                )

                            if frame.status == "ready":
                                review_note = st.text_input(
                                    "Review Note / 审核备注",
                                    value=frame.review_note,
                                    key=(
                                        f"storyboard_review_note_"
                                        f"{episode.episode_id}_"
                                        f"{storyboard_shot.shot_id}"
                                    ),
                                    placeholder="可选：需要调整什么？",
                                )
                                approve_col, change_col = st.columns(2)
                                with approve_col:
                                    if st.button(
                                        "✅ Approve / 批准",
                                        key=(
                                            f"approve_storyboard_"
                                            f"{episode.episode_id}_"
                                            f"{storyboard_shot.shot_id}"
                                        ),
                                        use_container_width=True,
                                    ):
                                        storyboard_service.review_frame(
                                            episode_id=episode.episode_id,
                                            scene_id=storyboard_scene.scene_id,
                                            shot_id=storyboard_shot.shot_id,
                                            review_status="approved",
                                            note=review_note,
                                        )
                                        st.rerun()
                                with change_col:
                                    if st.button(
                                        "📝 Needs Change / 需修改",
                                        key=(
                                            f"reject_storyboard_"
                                            f"{episode.episode_id}_"
                                            f"{storyboard_shot.shot_id}"
                                        ),
                                        use_container_width=True,
                                    ):
                                        storyboard_service.review_frame(
                                            episode_id=episode.episode_id,
                                            scene_id=storyboard_scene.scene_id,
                                            shot_id=storyboard_shot.shot_id,
                                            review_status="needs_change",
                                            note=review_note,
                                        )
                                        st.rerun()

                            render_record = (
                                shot_render_service.status_for(
                                    episode_id=episode.episode_id,
                                    scene_id=storyboard_scene.scene_id,
                                    shot_id=storyboard_shot.shot_id,
                                )
                            )
                            render_badge = {
                                "missing": "⬜ Not Rendered / 未渲染",
                                "rendering": "⏳ Rendering / 渲染中",
                                "rendered": "🎬 Rendered / 已渲染",
                                "stale": "🟠 Render Stale / 视频已过期",
                                "failed": "⚠️ Render Failed / 渲染失败",
                            }.get(
                                render_record.status,
                                "⬜ Not Rendered / 未渲染",
                            )
                            st.caption(render_badge)

                            video_bytes = shot_render_service.video_bytes(
                                render_record
                            )
                            if (
                                render_record.status == "rendered"
                                and video_bytes is not None
                            ):
                                st.video(video_bytes)
                                st.download_button(
                                    "⬇️ Download Shot MP4 / 下载镜头",
                                    data=video_bytes,
                                    file_name=(
                                        f"{storyboard_shot.shot_id}.mp4"
                                    ),
                                    mime="video/mp4",
                                    key=(
                                        f"download_shot_"
                                        f"{episode.episode_id}_"
                                        f"{storyboard_shot.shot_id}"
                                    ),
                                    use_container_width=True,
                                )
                            elif render_record.status == "failed":
                                st.warning(
                                    "这个镜头还没有成功渲染。"
                                    "可以安全地只重试这一条 Shot。"
                                )

                            if frame.approved_current and (
                                render_record.status
                                in {"missing", "stale", "failed"}
                            ):
                                render_label = (
                                    "🔄 Re-render Shot / 重渲镜头"
                                    if render_record.status
                                    in {"stale", "failed"}
                                    else "🎬 Render Shot / 渲染镜头"
                                )
                                if st.button(
                                    render_label,
                                    key=(
                                        f"render_shot_"
                                        f"{episode.episode_id}_"
                                        f"{storyboard_shot.shot_id}"
                                    ),
                                    type="primary",
                                    use_container_width=True,
                                ):
                                    with st.spinner(
                                        "🎬 Godot 正在渲染这个镜头…"
                                    ):
                                        rendered = (
                                            shot_render_service.render_shot(
                                                episode_id=episode.episode_id,
                                                scene_id=storyboard_scene.scene_id,
                                                shot_id=storyboard_shot.shot_id,
                                            )
                                        )
                                    if rendered.status == "rendered":
                                        st.rerun()
                                    else:
                                        st.warning(
                                            "镜头渲染暂未完成。"
                                            "请确认本机 Godot 与 ffmpeg 可用后重试。"
                                        )

                            button_label = (
                                "🔄 Refresh Frame / 更新分镜"
                                if frame.status in {"stale", "failed"}
                                or frame.review_status == "needs_change"
                                else "🖼️ Generate Frame / 生成分镜"
                            )
                            if st.button(
                                button_label,
                                key=(
                                    f"storyboard_{episode.episode_id}_"
                                    f"{storyboard_scene.scene_id}_"
                                    f"{storyboard_shot.shot_id}"
                                ),
                                use_container_width=True,
                            ):
                                with st.spinner(
                                    "🎬 正在用 Godot Director 拍摄规划画面…"
                                ):
                                    generated = (
                                        storyboard_service.generate_frame(
                                            episode_id=episode.episode_id,
                                            scene_id=storyboard_scene.scene_id,
                                            shot_id=storyboard_shot.shot_id,
                                        )
                                    )
                                if generated.status == "ready":
                                    st.rerun()
                                else:
                                    st.warning(
                                        "Storyboard capture 暂未完成。"
                                        "请确认本机 Godot 可用后重试。"
                                    )

                st.markdown("#### 🎞️ Script & Scene Breakdown / 剧本场景")
                for scene in episode.scenes:
                    with st.expander(
                        f"{scene.scene_id} · {scene.story_beat or 'SCENE'} · "
                        f"{scene.title or scene.description[:40]}",
                        expanded=False,
                    ):
                        with st.form(
                            f"edit_scene_form_{episode.episode_id}_{scene.scene_id}",
                            clear_on_submit=False,
                        ):
                            title = st.text_input(
                                "Scene Title / 场景名",
                                value=scene.title,
                            )
                            description = st.text_area(
                                "Scene Description / 场景描述",
                                value=scene.description,
                                height=100,
                            )
                            action_summary = st.text_area(
                                "Action / 动作",
                                value=scene.action_summary,
                                height=90,
                            )
                            dialogue_notes = st.text_area(
                                "Dialogue / Narration Notes / 对白与旁白",
                                value=scene.dialogue_notes,
                                height=90,
                            )
                            continuity_text = st.text_area(
                                "Continuity Notes / 连续性备注",
                                value="\n".join(scene.continuity_notes),
                                height=80,
                            )
                            st.caption(
                                "Assets · "
                                + (", ".join(scene.asset_ids) or "—")
                                + " · World · "
                                + (scene.location_asset_id or "—")
                            )
                            saved = st.form_submit_button(
                                "💾 Save Scene / 保存场景",
                                use_container_width=True,
                            )

                        if saved:
                            scene_service.update_scene(
                                episode_id=episode.episode_id,
                                scene_id=scene.scene_id,
                                title=title,
                                description=description,
                                action_summary=action_summary,
                                dialogue_notes=dialogue_notes,
                                continuity_notes=continuity_text.splitlines(),
                            )
                            st.rerun()

                        if scene.shots:
                            st.markdown("##### 🎥 Shot List / 镜头表")
                            for shot in scene.shots:
                                with st.container(border=True):
                                    st.caption(
                                        f"{shot.shot_id} · "
                                        f"{shot.duration_seconds:.1f}s · "
                                        f"{shot.shot_type}"
                                    )
                                    with st.form(
                                        f"edit_shot_{episode.episode_id}_"
                                        f"{scene.scene_id}_{shot.shot_id}",
                                        clear_on_submit=False,
                                    ):
                                        duration = st.number_input(
                                            "Duration / 时长（秒）",
                                            min_value=0.5,
                                            max_value=30.0,
                                            value=float(
                                                shot.duration_seconds
                                            ),
                                            step=0.5,
                                        )
                                        shot_type = st.text_input(
                                            "Shot Type / 镜头类型",
                                            value=shot.shot_type,
                                        )
                                        camera = st.text_input(
                                            "Camera / 机位与运动",
                                            value=shot.camera,
                                        )
                                        shot_action = st.text_area(
                                            "Action / 镜头动作",
                                            value=shot.action,
                                            height=80,
                                        )
                                        expression = st.text_input(
                                            "Expression / 表情",
                                            value=shot.expression,
                                        )

                                        blocking = shot.blocking
                                        if blocking is not None:
                                            st.markdown(
                                                "**🎭 Blocking / 角色走位**"
                                            )
                                            st.caption(
                                                f"{blocking.source.title()} · "
                                                f"{blocking.movement_style.title()} · "
                                                f"confidence {blocking.confidence:.0%}"
                                            )
                                            start_cols = st.columns(3)
                                            start_x = start_cols[0].number_input(
                                                "Start X",
                                                value=float(blocking.actor_start.x),
                                                step=0.5,
                                                key=f"start_x_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            start_y = start_cols[1].number_input(
                                                "Start Y",
                                                value=float(blocking.actor_start.y),
                                                step=0.5,
                                                key=f"start_y_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            start_z = start_cols[2].number_input(
                                                "Start Z",
                                                value=float(blocking.actor_start.z),
                                                step=0.5,
                                                key=f"start_z_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            end_cols = st.columns(3)
                                            end_x = end_cols[0].number_input(
                                                "End X",
                                                value=float(blocking.actor_end.x),
                                                step=0.5,
                                                key=f"end_x_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            end_y = end_cols[1].number_input(
                                                "End Y",
                                                value=float(blocking.actor_end.y),
                                                step=0.5,
                                                key=f"end_y_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            end_z = end_cols[2].number_input(
                                                "End Z",
                                                value=float(blocking.actor_end.z),
                                                step=0.5,
                                                key=f"end_z_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            facing_degrees = st.number_input(
                                                "Facing / 朝向（°）",
                                                value=float(blocking.facing_degrees),
                                                step=5.0,
                                                key=f"facing_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            movement_style = st.selectbox(
                                                "Movement / 走位方式",
                                                ["hold", "walk", "run"],
                                                index=["hold", "walk", "run"].index(
                                                    blocking.movement_style
                                                ),
                                                key=f"movement_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            baby_cols = st.columns(2)
                                            baby_x = baby_cols[0].number_input(
                                                "Baby Offset X",
                                                value=float(blocking.baby_offset.x),
                                                step=0.25,
                                                key=f"baby_x_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            baby_z = baby_cols[1].number_input(
                                                "Baby Offset Z",
                                                value=float(blocking.baby_offset.z),
                                                step=0.25,
                                                key=f"baby_z_{episode.episode_id}_{shot.shot_id}",
                                            )

                                        camera_motion = shot.camera_motion
                                        if camera_motion is not None:
                                            st.markdown(
                                                "**🎥 Camera Motion / 镜头运动**"
                                            )
                                            st.caption(
                                                f"{camera_motion.source.title()} · "
                                                f"{camera_motion.movement_mode.replace('_', ' ').title()} · "
                                                f"confidence {camera_motion.confidence:.0%}"
                                            )
                                            motion_mode = st.selectbox(
                                                "Motion Mode / 运动方式",
                                                [
                                                    "hold",
                                                    "push_in",
                                                    "pull_back",
                                                    "pan",
                                                    "follow",
                                                    "reveal",
                                                ],
                                                index=[
                                                    "hold",
                                                    "push_in",
                                                    "pull_back",
                                                    "pan",
                                                    "follow",
                                                    "reveal",
                                                ].index(camera_motion.movement_mode),
                                                key=f"camera_mode_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            easing = st.selectbox(
                                                "Easing / 缓动",
                                                ["smooth", "linear"],
                                                index=["smooth", "linear"].index(
                                                    camera_motion.easing
                                                ),
                                                key=f"camera_easing_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            cam_start = st.columns(3)
                                            cam_start_x = cam_start[0].number_input(
                                                "Cam Start X",
                                                value=float(camera_motion.start_position.x),
                                                step=0.5,
                                                key=f"cam_sx_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            cam_start_y = cam_start[1].number_input(
                                                "Cam Start Y",
                                                value=float(camera_motion.start_position.y),
                                                step=0.5,
                                                key=f"cam_sy_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            cam_start_z = cam_start[2].number_input(
                                                "Cam Start Z",
                                                value=float(camera_motion.start_position.z),
                                                step=0.5,
                                                key=f"cam_sz_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            cam_end = st.columns(3)
                                            cam_end_x = cam_end[0].number_input(
                                                "Cam End X",
                                                value=float(camera_motion.end_position.x),
                                                step=0.5,
                                                key=f"cam_ex_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            cam_end_y = cam_end[1].number_input(
                                                "Cam End Y",
                                                value=float(camera_motion.end_position.y),
                                                step=0.5,
                                                key=f"cam_ey_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            cam_end_z = cam_end[2].number_input(
                                                "Cam End Z",
                                                value=float(camera_motion.end_position.z),
                                                step=0.5,
                                                key=f"cam_ez_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            look_start = st.columns(3)
                                            look_start_x = look_start[0].number_input(
                                                "Look Start X",
                                                value=float(camera_motion.start_look_at.x),
                                                step=0.5,
                                                key=f"look_sx_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            look_start_y = look_start[1].number_input(
                                                "Look Start Y",
                                                value=float(camera_motion.start_look_at.y),
                                                step=0.5,
                                                key=f"look_sy_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            look_start_z = look_start[2].number_input(
                                                "Look Start Z",
                                                value=float(camera_motion.start_look_at.z),
                                                step=0.5,
                                                key=f"look_sz_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            look_end = st.columns(3)
                                            look_end_x = look_end[0].number_input(
                                                "Look End X",
                                                value=float(camera_motion.end_look_at.x),
                                                step=0.5,
                                                key=f"look_ex_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            look_end_y = look_end[1].number_input(
                                                "Look End Y",
                                                value=float(camera_motion.end_look_at.y),
                                                step=0.5,
                                                key=f"look_ey_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            look_end_z = look_end[2].number_input(
                                                "Look End Z",
                                                value=float(camera_motion.end_look_at.z),
                                                step=0.5,
                                                key=f"look_ez_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            fov_cols = st.columns(2)
                                            start_fov = fov_cols[0].number_input(
                                                "Start FOV",
                                                min_value=20.0,
                                                max_value=100.0,
                                                value=float(camera_motion.start_fov),
                                                step=1.0,
                                                key=f"fov_start_{episode.episode_id}_{shot.shot_id}",
                                            )
                                            end_fov = fov_cols[1].number_input(
                                                "End FOV",
                                                min_value=20.0,
                                                max_value=100.0,
                                                value=float(camera_motion.end_fov),
                                                step=1.0,
                                                key=f"fov_end_{episode.episode_id}_{shot.shot_id}",
                                            )

                                        performance_cues = shot.performance_cues
                                        edited_cues = []
                                        if performance_cues is not None:
                                            st.markdown(
                                                "**🎭 Performance Cues / 表演提示**"
                                            )
                                            cue_types = [
                                                "idle",
                                                "walk",
                                                "run",
                                                "attack",
                                                "look_at",
                                                "reaction",
                                                "celebrate",
                                            ]
                                            for cue_index, cue in enumerate(
                                                performance_cues
                                            ):
                                                st.caption(
                                                    f"{cue.cue_id} · "
                                                    f"{cue.source.title()}"
                                                )
                                                cue_cols = st.columns(4)
                                                cue_type = cue_cols[0].selectbox(
                                                    "Cue Type",
                                                    cue_types,
                                                    index=cue_types.index(
                                                        cue.cue_type
                                                    ),
                                                    key=(
                                                        f"cue_type_{episode.episode_id}_"
                                                        f"{shot.shot_id}_{cue_index}"
                                                    ),
                                                )
                                                cue_start = cue_cols[1].number_input(
                                                    "Start (s)",
                                                    min_value=0.0,
                                                    max_value=float(duration),
                                                    value=min(
                                                        float(cue.start_seconds),
                                                        float(duration),
                                                    ),
                                                    step=0.1,
                                                    key=(
                                                        f"cue_start_{episode.episode_id}_"
                                                        f"{shot.shot_id}_{cue_index}"
                                                    ),
                                                )
                                                cue_duration = cue_cols[2].number_input(
                                                    "Cue Duration",
                                                    min_value=0.05,
                                                    max_value=30.0,
                                                    value=float(
                                                        cue.duration_seconds
                                                    ),
                                                    step=0.1,
                                                    key=(
                                                        f"cue_duration_{episode.episode_id}_"
                                                        f"{shot.shot_id}_{cue_index}"
                                                    ),
                                                )
                                                cue_intensity = cue_cols[3].number_input(
                                                    "Intensity",
                                                    min_value=0.0,
                                                    max_value=1.0,
                                                    value=float(cue.intensity),
                                                    step=0.05,
                                                    key=(
                                                        f"cue_intensity_{episode.episode_id}_"
                                                        f"{shot.shot_id}_{cue_index}"
                                                    ),
                                                )
                                                edited_cues.append(
                                                    PerformanceCue(
                                                        cue_id=cue.cue_id,
                                                        cue_type=cue_type,
                                                        start_seconds=cue_start,
                                                        duration_seconds=cue_duration,
                                                        intensity=cue_intensity,
                                                        target=cue.target,
                                                        direction_degrees=cue.direction_degrees,
                                                        source="creator",
                                                        confidence=1.0,
                                                    )
                                                )

                                        shot_continuity = st.text_area(
                                            "Shot Continuity / 镜头连续性",
                                            value="\n".join(
                                                shot.continuity_notes
                                            ),
                                            height=70,
                                        )
                                        save_shot = st.form_submit_button(
                                            "💾 Save Shot / 保存镜头",
                                            use_container_width=True,
                                        )
                                    if save_shot:
                                        shot_service.update_shot(
                                            episode_id=episode.episode_id,
                                            scene_id=scene.scene_id,
                                            shot_id=shot.shot_id,
                                            duration_seconds=duration,
                                            shot_type=shot_type,
                                            camera=camera,
                                            action=shot_action,
                                            expression=expression,
                                            continuity_notes=(
                                                shot_continuity.splitlines()
                                            ),
                                            blocking=(
                                                ShotBlockingSpec(
                                                    actor_start=ShotBlockingPoint(
                                                        x=start_x,
                                                        y=start_y,
                                                        z=start_z,
                                                    ),
                                                    actor_end=ShotBlockingPoint(
                                                        x=end_x,
                                                        y=end_y,
                                                        z=end_z,
                                                    ),
                                                    facing_degrees=facing_degrees,
                                                    baby_offset=ShotBlockingPoint(
                                                        x=baby_x,
                                                        y=0.0,
                                                        z=baby_z,
                                                    ),
                                                    movement_style=movement_style,
                                                    source="creator",
                                                    confidence=1.0,
                                                )
                                                if blocking is not None
                                                else None
                                            ),
                                            camera_motion=(
                                                ShotCameraMotionSpec(
                                                    start_position=ShotBlockingPoint(
                                                        x=cam_start_x,
                                                        y=cam_start_y,
                                                        z=cam_start_z,
                                                    ),
                                                    end_position=ShotBlockingPoint(
                                                        x=cam_end_x,
                                                        y=cam_end_y,
                                                        z=cam_end_z,
                                                    ),
                                                    start_look_at=ShotBlockingPoint(
                                                        x=look_start_x,
                                                        y=look_start_y,
                                                        z=look_start_z,
                                                    ),
                                                    end_look_at=ShotBlockingPoint(
                                                        x=look_end_x,
                                                        y=look_end_y,
                                                        z=look_end_z,
                                                    ),
                                                    start_fov=start_fov,
                                                    end_fov=end_fov,
                                                    movement_mode=motion_mode,
                                                    easing=easing,
                                                    source="creator",
                                                    confidence=1.0,
                                                )
                                                if camera_motion is not None
                                                else None
                                            ),
                                            performance_cues=(
                                                edited_cues
                                                if performance_cues is not None
                                                else None
                                            ),
                                        )
                                        st.rerun()

                                    if st.button(
                                        "🎬 Stage Shot / 导演模式",
                                        key=(
                                            f"stage_director_{episode.episode_id}_"
                                            f"{scene.scene_id}_{shot.shot_id}"
                                        ),
                                        type="primary",
                                        use_container_width=True,
                                    ):
                                        try:
                                            session = director_service.export(
                                                episode_id=episode.episode_id,
                                                scene_id=scene.scene_id,
                                                shot_id=shot.shot_id,
                                            )
                                            st.session_state[
                                                "director_last_session"
                                            ] = session.model_dump(
                                                mode="json"
                                            )
                                            st.success(
                                                "🎬 Director Shot ready / "
                                                "导演镜头已准备 · "
                                                f"{session.director_session_id} · "
                                                f"{session.animation_intent.title()} · "
                                                f"{session.duration_seconds:.1f}s"
                                            )
                                        except ValueError as exc:
                                            st.error(str(exc))

                                    last_director = st.session_state.get(
                                        "director_last_session"
                                    )
                                    if (
                                        isinstance(last_director, dict)
                                        and last_director.get("episode_id")
                                        == episode.episode_id
                                        and last_director.get("scene_id")
                                        == scene.scene_id
                                        and last_director.get("shot_id")
                                        == shot.shot_id
                                    ):
                                        st.info(
                                            "🎥 Godot Director payload ready · "
                                            f"Camera {last_director.get('camera', {}).get('movement', '')} · "
                                            f"Actor {last_director.get('character_asset_id', '')} · "
                                            f"World {last_director.get('world_asset_id', '—')}"
                                        )
            else:
                st.info(
                    "下一步：Script & Scene Breakdown / 剧本与场景拆解。"
                    " 如果 Story 有 Story Beats，就可以直接生成。"
                )
