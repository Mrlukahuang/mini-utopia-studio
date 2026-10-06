from pathlib import Path

from studio.models.avatar import AvatarAppearance, BodyType
from studio.ui.creator.avatar_catalog import (
    EYE_STYLE_OPTIONS,
    HAIR_STYLE_OPTIONS,
    SPECIES_HEAD_OPTIONS,
    SURFACE_OPTIONS,
    allowed_eye_ids,
    allowed_hair_ids,
    allowed_surface_ids,
    species_default_surface,
)


ROOT = Path(__file__).resolve().parents[1]


def test_avatar_catalog_has_child_visible_v1_minimums():
    assert len(SPECIES_HEAD_OPTIONS) >= 3
    assert len(SURFACE_OPTIONS) >= 3
    assert len(EYE_STYLE_OPTIONS) >= 3
    assert len(HAIR_STYLE_OPTIONS) >= 3


def test_species_compatibility_rules_are_constrained():
    assert allowed_surface_ids("species_head_human_v1") == ("skin",)
    assert "wool" in allowed_surface_ids("species_head_sheep_v1")
    assert allowed_surface_ids("species_head_robot_v1") == ("metal",)
    assert "eyes_robot_v1" in allowed_eye_ids("species_head_robot_v1")
    assert "hair_none" in allowed_hair_ids("species_head_cloud_v1")


def test_species_default_surfaces_match_identity():
    assert species_default_surface("species_head_human_v1") == "skin"
    assert species_default_surface("species_head_sheep_v1") == "wool"
    assert species_default_surface("species_head_robot_v1") == "metal"
    assert species_default_surface("species_head_cat_v1") == "fur"
    assert species_default_surface("species_head_cloud_v1") == "cloud"


def test_avatar_appearance_can_store_modular_selection():
    appearance = AvatarAppearance(
        customized=True,
        body_type=BodyType.CHUBBY,
        species_head_id="species_head_sheep_v1",
        surface_type="wool",
        surface_color_hex="#F6F1E8",
        eye_style_id="eyes_sparkle_v1",
        eye_color_hex="#7A5238",
        hair_style_id="hair_bob_v1",
        hair_color_hex="#F7B7D2",
    )

    restored = AvatarAppearance.model_validate(
        appearance.model_dump(mode="json")
    )

    assert restored == appearance


def test_character_factory_contains_avatar_editor_and_live_preview():
    factory = (
        ROOT / "studio" / "ui" / "creator" / "character_factory.py"
    ).read_text(encoding="utf-8")
    editor = (
        ROOT / "studio" / "ui" / "creator" / "avatar_editor.py"
    ).read_text(encoding="utf-8")
    preview = (
        ROOT / "studio" / "ui" / "creator" / "avatar_preview.py"
    ).read_text(encoding="utf-8")

    assert "render_avatar_appearance_editor" in factory
    assert '"avatar": avatar' in factory
    assert "Species Head / 种族头型" in editor
    assert "Body Type / 体型" in editor
    assert "Surface / 皮肤 · 毛发 · 材质" in editor
    assert "Eyes / 眼型" in editor
    assert "Hair Style / 发型" in editor
    assert "render_avatar_preview(result)" in editor
    assert "Live Avatar Preview / 实时预览" in preview
