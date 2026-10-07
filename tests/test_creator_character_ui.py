from studio.ui.creator.character_factory import (
    english_level_label,
    relative_height_label,
)


def test_english_level_labels_cover_full_scale():
    assert "Almost no English" in english_level_label(1)
    assert "Native" in english_level_label(10)


def test_relative_height_label_uses_reference_names():
    label = relative_height_label(
        125,
        ["Chelsea", "Charlotte"],
        [110, 140],
    )

    assert "Chelsea" in label
    assert "Charlotte" in label
    assert "Between" in label


def test_relative_height_label_handles_large_character():
    label = relative_height_label(
        250,
        ["Chelsea", "Charlotte"],
        [110, 140],
    )

    assert "Charlotte" in label
    assert "Much taller" in label


def test_character_factory_returns_to_library_after_approval():
    from pathlib import Path

    source = Path("studio/ui/creator/character_factory.py").read_text()
    assert 'pending_app_page = "🎭 My Characters"' in source



def test_character_factory_is_child_first_and_saves_without_image_api():
    from pathlib import Path

    source = Path("studio/ui/creator/character_factory.py").read_text(
        encoding="utf-8"
    )

    assert "Start My Hero / 开始创造我的角色" in source
    assert "Make a hero of your own!" in source
    assert "More choices / 更多设定（可选）" in source
    assert "More personality details / 更多性格设定（可选）" in source
    assert "Pick a first outfit / 选第一套穿搭" in source
    assert "More details / 更多设定（可选）" in source
    assert "Save My Hero / 保存我的角色" in source
    assert "profile_can_save = not missing and bool(name)" in source
    assert 'pending_app_page = "🎭 My Characters"' in source
    assert "上面的 Save My Hero 可以直接保存可玩角色" in source

    save_button = source.index("💖 Save My Hero / 保存我的角色")
    image_gate = source.index("ctx.character_masters.is_available")
    assert save_button < image_gate
