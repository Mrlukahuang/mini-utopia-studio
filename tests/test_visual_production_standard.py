import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_visual_production_standard_locks_c_plus_and_hero_assembly():
    text = (ROOT / "docs" / "MINI_UTOPIA_VISUAL_PRODUCTION_STANDARD_V1.md").read_text(
        encoding="utf-8"
    )

    assert "Soft Blocky Toy Diorama + Constructed Toy Grammar" in text
    assert "Structure boxy. Silhouette rounded. Hero may be organic." in text
    assert "Unified Hero Assembly" in text
    assert "Concept image" in text
    assert "Reconstruction reference" in text


def test_palette_candidates_are_versioned_and_not_marked_final():
    path = ROOT / "godot" / "config" / "style" / "core_palette_candidates_v0_9.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["status"] == "calibration_candidate"
    assert data["schema_version"] == "0.9"
    assert data["candidate_id"] == "storybook_macaron_b"
    assert data["colors"]["cream_base"] == "#EEDFC7"
    assert data["colors"]["deep_ink"] == "#403A57"
    assert data["colors"]["glow_gold"] == "#FFC83D"
    assert len(data["colors"]) >= 16


def test_static_slots_and_runtime_semantic_roles_stay_separate():
    slots = json.loads(
        (ROOT / "godot" / "config" / "style" / "semantic_slots_v0_1.json").read_text(
            encoding="utf-8"
        )
    )
    roles = json.loads(
        (ROOT / "godot" / "config" / "style" / "semantic_roles_v0_1.json").read_text(
            encoding="utf-8"
        )
    )

    assert "wood_base" in slots["slots"]
    assert "foliage_base" in slots["slots"]
    assert "interact" not in slots["slots"]
    assert roles["roles"]["interact"] == "glow_gold"
    assert roles["roles"]["danger"] == "strawberry"


def test_style_calibration_lab_scene_contract():
    scene = (ROOT / "godot" / "scenes" / "style_calibration_lab.tscn").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "godot" / "scripts" / "style_calibration_lab.gd").read_text(
        encoding="utf-8"
    )

    assert 'res://scripts/style_calibration_lab.gd' in scene
    assert 'res://config/style/core_palette_candidates_v0_9.json' in script
    assert '"COLOR"' in script
    assert '"GRAYSCALE"' in script
    assert '"SILHOUETTE"' in script
    assert 'material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED' in script
    assert '_add_palette_row_label("RAW"' in script
    assert '_add_palette_row_label("LIT"' in script
    assert 'env.background_color = Color("#8E8B86")' in script
    assert "Environment.TONE_MAPPER_FILMIC" in script
    assert "env.tonemap_exposure = 1.0" in script
