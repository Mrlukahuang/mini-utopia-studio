from pathlib import Path

from studio.models.avatar import AvatarAppearance, BodyType
from studio.runtime.avatar_preview_3d import BODY_WIDTH_SCALE, HEAD_WIDTH_SCALE
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
    assert "legacy_visual_updates(draft, avatar)" in factory
    assert "Species Head / 种族头型" in editor
    assert "Body Type / 体型" in editor
    assert "Surface / 皮肤 · 毛发 · 材质" in editor
    assert "Eyes / 眼型" in editor
    assert "Hair Style / 发型" in editor
    assert "render_avatar_preview(result)" in editor
    assert "Live 3D Avatar / 实时 3D 预览" in preview
    assert "components.html(" in preview
    assert "height: int = 620" in preview
    assert "height=height" in preview
    assert "avatar-stage" not in preview


def test_webgl_avatar_preview_mirrors_godot_contract():
    runtime = (
        ROOT / "studio" / "runtime" / "avatar_preview_3d.py"
    ).read_text(encoding="utf-8")
    contract = (
        ROOT / "godot" / "scripts" / "avatar_contract.gd"
    ).read_text(encoding="utf-8")

    assert "THREE.WebGLRenderer" in runtime
    assert "OrbitControls" in runtime
    assert "Idle" in runtime
    assert "Walk" in runtime
    assert "Run" in runtime
    assert "Jump" in runtime

    for socket_name in (
        "Socket_Weapon_R",
        "Socket_Weapon_L",
        "Socket_Backpack",
        "Socket_Wings",
        "Socket_Accessory",
    ):
        assert socket_name in runtime
        assert socket_name in contract

    assert '"slim": 0.84' in runtime
    assert '"standard": 1.0' in runtime
    assert '"chubby": 1.16' in runtime
    assert "return 0.84" in contract
    assert "return 1.16" in contract


def test_body_type_changes_body_but_not_q_head_shape():
    assert BODY_WIDTH_SCALE == {
        "slim": 0.84,
        "standard": 1.0,
        "chubby": 1.16,
    }
    assert HEAD_WIDTH_SCALE == {
        "slim": 1.0,
        "standard": 1.0,
        "chubby": 1.0,
    }

    runtime = (
        ROOT / "studio" / "runtime" / "avatar_preview_3d.py"
    ).read_text(encoding="utf-8")
    godot_contract = (
        ROOT / "godot" / "scripts" / "avatar_contract.gd"
    ).read_text(encoding="utf-8")
    godot_preview = (
        ROOT / "godot" / "scripts" / "avatar_contract_preview.gd"
    ).read_text(encoding="utf-8")

    assert "const headWidth = DATA.headWidthScale[A.body_type] || 1;" in runtime
    assert "sphereGeo(.70*headWidth,.69,.67)" in runtime
    assert "head_width_scale" in godot_contract
    assert "return 1.0" in godot_contract
    assert "0.70 * head_scale" in godot_preview
    assert "0.15 * head_scale" in godot_preview


def test_each_non_none_hair_style_has_visible_3d_geometry():
    runtime = (
        ROOT / "studio" / "runtime" / "avatar_preview_3d.py"
    ).read_text(encoding="utf-8")

    assert "HairFringe" in runtime
    assert "ShortSweep" in runtime
    assert "BobSideL" in runtime
    assert "BobSideR" in runtime
    assert "LongSideL" in runtime
    assert "LongSideR" in runtime
    assert "Ponytail" in runtime
    assert "Fluff" in runtime
    assert "[0,2.05,.61]" in runtime
