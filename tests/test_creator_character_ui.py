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
