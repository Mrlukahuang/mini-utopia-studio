from pathlib import Path

from studio.core.product_boundary import (
    ARCHITECTURE_INVARIANT,
    CANONICAL_METADATA_OWNER,
    GODOT_CREATOR_MUTATION_POLICY,
    GODOT_PRODUCT_ROLE,
    GODOT_USER_DATA_ROLE,
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
