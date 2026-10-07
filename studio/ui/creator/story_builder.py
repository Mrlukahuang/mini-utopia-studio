import streamlit as st

from studio.core.enums import AssetType, ReviewStatus, StoryMode


_BEAT_WIDGET_KEYS = {
    "arrive": "story_hook",
    "discover": "story_discovery",
    "problem": "story_conflict",
    "adventure": "story_adventure",
    "surprise": "story_twist",
    "portal": "story_ending",
}


def _apply_pending_ai_suggestion() -> None:
    pending = st.session_state.pop("story_ai_suggestion_pending", None)
    if not pending:
        return
    for field, key in _BEAT_WIDGET_KEYS.items():
        value = pending.get(field)
        if isinstance(value, str) and value.strip():
            st.session_state[key] = value.strip()
    st.session_state["story_ai_suggestion_applied"] = True


def render_story_builder(ctx, *, universe) -> None:
    """Creator-facing structured Story Builder with optional AI beat proposals."""

    _apply_pending_ai_suggestion()

    st.header("✍️ Story Builder")
    st.write(
        "把已经做好的角色、世界和道具组合成一个可以继续制作的 Story。"
        " Story 只保存 Asset ID，不复制角色或世界。"
    )

    if st.session_state.pop("story_ai_suggestion_applied", False):
        st.success(
            "✨ AI 提案已经放进 6 个 Story Beats。"
            " 你可以随便改，只有点击 Save 才会保存。"
        )

    mode_label = st.radio(
        "Story Mode / 故事模式",
        ["🌎 Mini Utopia Canon", "🧪 Playground"],
        horizontal=True,
        key="story_builder_mode",
    )
    story_mode = (
        StoryMode.CANON
        if mode_label == "🌎 Mini Utopia Canon"
        else StoryMode.PLAYGROUND
    )

    if story_mode == StoryMode.CANON:
        st.caption(
            "Canon rhythm · "
            + " → ".join(universe.story_formula)
        )
        st.info(
            "Canon Story 会绑定 Mini Utopia Universe，并沿用 Traveler / Portal / 连续性规则。"
        )
    else:
        st.caption("Playground · No canon. Just create.")

    characters = [
        asset
        for asset in ctx.repository.list_assets(AssetType.CHARACTER)
        if asset.status != ReviewStatus.ARCHIVED
    ]
    worlds = [
        asset
        for asset in ctx.repository.list_assets(AssetType.LOCATION)
        if asset.status != ReviewStatus.ARCHIVED
    ]
    props = [
        asset
        for asset in ctx.repository.list_assets(AssetType.PROP)
        if asset.status != ReviewStatus.ARCHIVED
    ]

    if not characters:
        st.warning("还没有 Character。先创建至少一个角色。")
    if not worlds:
        st.warning("还没有 World / Location。先创建至少一个世界。")

    with st.form("story_builder_form", clear_on_submit=False):
        title = st.text_input(
            "Story Title / 故事名字",
            placeholder="例如：新手村的第一扇神秘传送门",
            key="story_title",
        )
        premise = st.text_area(
            "Premise / 一句话发生什么？",
            placeholder="例如：Traveler 在新手村发现山顶的骷髅兵守着一把会发光的钥匙……",
            height=100,
            key="story_premise",
        )

        left, right = st.columns(2, gap="large")
        with left:
            selected_characters = st.multiselect(
                "Characters / 角色",
                characters,
                format_func=lambda asset: asset.display_name,
                key="story_characters",
            )
            selected_world = st.selectbox(
                "World / 世界",
                [None, *worlds],
                format_func=lambda asset: (
                    "选择一个世界…"
                    if asset is None
                    else asset.display_name
                ),
                key="story_world",
            )
        with right:
            selected_props = st.multiselect(
                "Props / 道具（可选）",
                props,
                format_func=lambda asset: asset.display_name,
                key="story_props",
            )

        st.divider()
        st.subheader("Story Beats / 故事节奏")
        if ctx.story_suggestions.available:
            st.caption(
                "✨ AI 可以先提 6 个草案；它不会自动保存，"
                "每一段都可以继续改。"
            )
        else:
            st.caption(
                "手动 Story Builder 随时可用。连接 Structured Text provider 后，"
                "这里会出现 AI Story Suggestions。"
            )

        hook = st.text_area(
            "1. ARRIVE / Hook · 怎么进入故事？",
            placeholder="Traveler 来到哪里？第一眼看到什么？",
            height=80,
            key="story_hook",
        )
        discovery = st.text_area(
            "2. DISCOVER · 发现了什么？",
            placeholder="一个秘密、角色、入口、奇怪现象或新目标。",
            height=80,
            key="story_discovery",
        )
        conflict = st.text_area(
            "3. PROBLEM · 问题是什么？",
            placeholder="什么阻止 Traveler 继续？",
            height=80,
            key="story_conflict",
        )
        adventure = st.text_area(
            "4. ADVENTURE · 接下来做什么？",
            placeholder="探索、追逐、解谜、合作或战斗。",
            height=80,
            key="story_adventure",
        )
        twist = st.text_area(
            "5. SURPRISE · 意外是什么？",
            placeholder="事情和一开始想的不一样在哪里？",
            height=80,
            key="story_twist",
        )
        ending = st.text_area(
            "6. PORTAL / NEXT WORLD · 怎么结束？",
            placeholder="解决、悬念、Portal 出现，或者留下下一集线索。",
            height=80,
            key="story_ending",
        )

        can_suggest = bool(
            ctx.story_suggestions.available
            and premise.strip()
            and selected_characters
            and selected_world is not None
        )
        can_save = bool(
            title.strip()
            and premise.strip()
            and selected_characters
            and selected_world is not None
        )
        suggest_col, save_col = st.columns(2)
        with suggest_col:
            suggest_submitted = st.form_submit_button(
                "✨ Suggest Story Beats / AI 提案",
                use_container_width=True,
                disabled=not can_suggest,
            )
        with save_col:
            submitted = st.form_submit_button(
                "💾 Save Structured Story / 保存故事",
                type="primary",
                use_container_width=True,
                disabled=not can_save,
            )

    if suggest_submitted:
        try:
            world_profile = (
                selected_world.metadata.get("world_profile", {})
                if selected_world is not None
                else {}
            )
            suggestions = ctx.story_suggestions.suggest(
                title=title,
                premise=premise,
                story_mode=story_mode.value,
                character_names=[
                    asset.display_name
                    for asset in selected_characters
                ],
                world_name=(
                    selected_world.display_name
                    if selected_world is not None
                    else ""
                ),
                world_context={
                    "world_type": world_profile.get("world_type", ""),
                    "mood": world_profile.get("mood", []),
                    "landmarks": world_profile.get("landmark_ideas", []),
                    "portal_form": world_profile.get("portal_form", ""),
                },
                prop_names=[
                    asset.display_name
                    for asset in selected_props
                ],
            )
            st.session_state["story_ai_suggestion_pending"] = (
                suggestions.model_dump(mode="json")
            )
            st.rerun()
        except Exception as exc:
            st.error(f"AI Story suggestion failed / 提案失败: {exc}")
        return

    if not submitted:
        return

    asset_ids = [
        *(asset.asset_id for asset in selected_characters),
        selected_world.asset_id,
        *(asset.asset_id for asset in selected_props),
    ]

    story = ctx.stories.create_story(
        title=title.strip(),
        premise=premise.strip(),
        mode=story_mode,
        universe_id=(
            universe.universe_id
            if story_mode == StoryMode.CANON
            else None
        ),
        asset_ids=asset_ids,
        hook=hook.strip(),
        discovery=discovery.strip(),
        conflict=conflict.strip(),
        adventure=adventure.strip(),
        twist=twist.strip(),
        ending=ending.strip(),
    )

    st.success(f"Story saved / 已保存：{story.story_id}")
    st.session_state.pending_app_page = "📖 Stories"
    st.rerun()
