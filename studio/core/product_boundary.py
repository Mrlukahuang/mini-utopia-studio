"""Locked product-surface boundaries for Mini Utopia.

These constants are intentionally small and dependency-free so later UI,
Bridge and runtime code can assert the same architecture contract.
"""

CANONICAL_METADATA_OWNER = "python_core_repository"

STREAMLIT_PRODUCT_ROLE = "studio_view"
STREAMLIT_CREATOR_MUTATION_POLICY = "read_only_target"

GODOT_PRODUCT_ROLE = "creator_and_game"
GODOT_CREATOR_MUTATION_POLICY = "bridge_only"

RUNTIME_JSON_ROLE = "transport_only"
GODOT_USER_DATA_ROLE = "cache_or_session_only"

ARCHITECTURE_INVARIANT = (
    "Streamlit may view. Godot may create and edit. Python Core owns the truth."
)


# Migration-era Streamlit editors are preserved temporarily for data access,
# but they are frozen: do not add new child-facing editing capability here.
FROZEN_STREAMLIT_CREATOR_SURFACES = (
    "character_factory",
    "dressing_room",
    "my_stuff_equipment_editing",
)
