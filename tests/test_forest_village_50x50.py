import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = (
    ROOT / "godot" / "config" / "worlds" / "forest_village_50x50_v0_1.json"
)


def test_forest_village_layout_is_true_50x50_candidate_b_slice():
    data = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))

    assert data["world_id"] == "forest_village_50x50_v01"
    assert data["size_meters"] == [50, 50]
    assert data["profile_id"] == "core_candidate_b"
    assert data["spawn"] == [0.0, 1.2, 20.0]


def test_forest_village_uses_real_golden_forest_and_medieval_assets():
    data = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in data["anchors"]]

    assert ids.count("medieval_home") == 3
    assert ids.count("medieval_tower") == 1
    assert ids.count("medieval_bridge") == 1
    assert ids.count("forest_tree_round") >= 8
    assert ids.count("forest_tree_branching") >= 4
    assert ids.count("forest_bush") >= 8
    assert ids.count("forest_rock") >= 6


def test_forest_village_playable_scene_has_player_camera_and_generated_world():
    scene = (
        ROOT / "godot" / "scenes" / "forest_village_50x50_v0_1.tscn"
    ).read_text(encoding="utf-8")
    script = (
        ROOT / "godot" / "scripts" / "forest_village_50x50.gd"
    ).read_text(encoding="utf-8")

    assert 'res://scenes/player.tscn' in scene
    assert 'res://scripts/camera_rig.gd' in scene
    assert 'res://scripts/forest_village_50x50.gd' in scene
    assert 'GoldenAnchorRuntime.instantiate_anchor' in script
    assert '"core_candidate_b"' in script
    assert '_build_boundary()' in script
    assert '_box_with_collision(' in script
    assert '_add_proxy_collider(' in script


def test_forest_village_layout_keeps_major_assets_inside_world_boundary():
    data = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))

    for entry in data["anchors"]:
        x, _y, z = entry["position"]
        assert -24.0 <= x <= 24.0
        assert -24.0 <= z <= 24.0
