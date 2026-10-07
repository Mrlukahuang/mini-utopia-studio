from __future__ import annotations

import streamlit as st

from studio.services.episode_service import EpisodeService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService


def render_episode_library(ctx) -> None:
    st.header("🎬 Episodes / 剧集")
    st.write(
        "Episode 是把 Story 变成可以继续拆 Scene、Shot、Camera 的制作容器。"
        " 它继续引用同一批角色、世界和道具，不复制资产。"
    )

    episode_service = EpisodeService(ctx.repository)
    scene_service = SceneBreakdownService(ctx.repository)
    shot_service = ShotPlanService(ctx.repository)
    episodes = episode_service.list_episodes()
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
                                        )
                                        st.rerun()
            else:
                st.info(
                    "下一步：Script & Scene Breakdown / 剧本与场景拆解。"
                    " 如果 Story 有 Story Beats，就可以直接生成。"
                )
