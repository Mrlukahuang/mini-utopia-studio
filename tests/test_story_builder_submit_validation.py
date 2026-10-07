from pathlib import Path

from studio.ui.creator.story_builder import _missing_required_fields


ROOT = Path(__file__).resolve().parents[1]


def test_story_builder_required_field_validation_is_post_submit_and_explicit():
    assert _missing_required_fields(
        title="",
        premise="",
        selected_characters=[],
        selected_world=None,
        require_title=True,
    ) == [
        "Story Title / 故事名字",
        "Premise / 一句话发生什么",
        "Characters / 角色",
        "World / 世界",
    ]

    assert _missing_required_fields(
        title="Nancy's First Portal Adventure",
        premise="Nancy and Nova find a portal.",
        selected_characters=["nancy"],
        selected_world=object(),
        require_title=True,
    ) == []


def test_story_builder_save_button_is_not_disabled_by_form_widget_state():
    source = (
        ROOT / "studio" / "ui" / "creator" / "story_builder.py"
    ).read_text(encoding="utf-8")

    save_block = source.split(
        '"💾 Save Structured Story / 保存故事"'
    )[1].split(")", 1)[0]
    assert "disabled=" not in save_block

    assert "Missing before Save" in source
    assert "AI 提案还缺少 / Missing" in source
    assert "disabled=not ctx.story_suggestions.available" in source
