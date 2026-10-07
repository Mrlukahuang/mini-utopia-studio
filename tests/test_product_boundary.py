from pathlib import Path

from studio.core.product_boundary import (
    ARCHITECTURE_INVARIANT,
    CANONICAL_METADATA_OWNER,
    GODOT_CREATOR_MUTATION_POLICY,
    GODOT_PRODUCT_ROLE,
    GODOT_USER_DATA_ROLE,
    FROZEN_STREAMLIT_CREATOR_SURFACES,
    RUNTIME_JSON_ROLE,
    STREAMLIT_CREATOR_MUTATION_POLICY,
    STREAMLIT_PRODUCT_ROLE,
)


def test_creator_architecture_boundary_is_locked():
    assert CANONICAL_METADATA_OWNER == "python_core_repository"
    assert STREAMLIT_PRODUCT_ROLE == "studio_view"
    assert STREAMLIT_CREATOR_MUTATION_POLICY == "read_only_target"
    assert GODOT_PRODUCT_ROLE == "creator_and_game"
    assert GODOT_CREATOR_MUTATION_POLICY == "bridge_only"
    assert RUNTIME_JSON_ROLE == "transport_only"
    assert GODOT_USER_DATA_ROLE == "cache_or_session_only"
    assert FROZEN_STREAMLIT_CREATOR_SURFACES == (
        "character_factory",
        "dressing_room",
        "my_stuff_equipment_editing",
    )
    assert ARCHITECTURE_INVARIANT == (
        "Streamlit may view. Godot may create and edit. "
        "Python Core owns the truth."
    )


def test_architecture_doc_names_single_source_of_truth_and_migration_rule():
    source = Path(
        "docs/MINI_UTOPIA_CREATOR_ARCHITECTURE_V1.md"
    ).read_text(encoding="utf-8")

    assert "One source of truth" in source
    assert "Godot Creator/Game" in source
    assert "through Bridge only" in source
    assert "Streamlit Studio" in source
    assert "No in target architecture" in source
    assert "Runtime/export JSON" in source
    assert "transport only" in source
    assert "Open in Mini Utopia" in source
    assert "do not delete existing saved Creator data" in source



def test_frozen_streamlit_creator_surfaces_show_migration_notice():
    sources = {
        "character_factory": Path(
            "studio/ui/creator/character_factory.py"
        ).read_text(encoding="utf-8"),
        "dressing_room": Path(
            "studio/ui/creator/dressing_room.py"
        ).read_text(encoding="utf-8"),
        "my_stuff_equipment_editing": Path(
            "studio/ui/creator/my_stuff.py"
        ).read_text(encoding="utf-8"),
    }

    for surface in FROZEN_STREAMLIT_CREATOR_SURFACES:
        assert "render_legacy_creator_notice" in sources[surface]

    notice = Path(
        "studio/ui/creator/migration_notice.py"
    ).read_text(encoding="utf-8")
    assert "Open in Mini Utopia" in notice
    assert "不会继续扩展在 Streamlit" in notice
