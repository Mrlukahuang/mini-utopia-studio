from __future__ import annotations

import streamlit as st

from studio.services.episode_service import EpisodeService


def render_episode_library(ctx) -> None:
    st.header("🎬 Episodes / 剧集")
    st.write(
        "Episode 是把 Story 变成可以继续拆 Scene、Shot、Camera 的制作容器。"
        " 它继续引用同一批角色、世界和道具，不复制资产。"
    )

    episodes = EpisodeService(ctx.repository).list_episodes()
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
                st.metric("Assets", len(episode.asset_ids))

            st.caption(
                "🌍 World · "
                + (episode.world_asset_id or "—")
                + " · 🐣 Baby · "
                + (episode.active_baby_id or "—")
                + " · 🧠 Memory refs · "
                + str(len(episode.continuity_memory_ids))
            )

            if episode.scenes:
                with st.expander("Scenes / 场景", expanded=False):
                    for scene in episode.scenes:
                        st.write(
                            f"🎞️ **{scene.scene_id}** · "
                            f"{scene.description or 'No description yet'} · "
                            f"{len(scene.shots)} shots"
                        )
            else:
                st.info("下一步：Script & Scene Breakdown / 剧本与场景拆解")
