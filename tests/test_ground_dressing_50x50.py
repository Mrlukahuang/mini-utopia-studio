import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_storybook_meadow_profile_is_rich_and_deterministic():
    profile = json.loads(
        (
            ROOT
            / "godot"
            / "config"
            / "ground"
            / "storybook_meadow_v0_1.json"
        ).read_text(encoding="utf-8")
    )

    assert profile["profile_id"] == "storybook_meadow_v0_1"
    assert profile["seed"] == 50206
    assert profile["dressing"]["grass_tufts"] >= 70
    assert profile["dressing"]["flower_clusters"] >= 20
    assert profile["dressing"]["pebbles"] >= 40
    assert profile["dressing"]["mushrooms"] >= 10
    assert len(profile["ground"]["patches"]) >= 6
    assert len(profile["gardens"]) == 3


def test_rich_forest_village_is_true_50x50_and_uses_candidate_b():
    layout = json.loads(
        (
            ROOT
            / "godot"
            / "config"
            / "worlds"
            / "forest_village_50x50_rich_v0_2.json"
        ).read_text(encoding="utf-8")
    )

    assert layout["size_meters"] == [50, 50]
    assert layout["profile_id"] == "core_candidate_b"
    assert layout["ground_profile"].endswith("storybook_meadow_v0_1.json")
    assert len(layout["main_path"]) >= 8
    assert len(layout["branch_paths"]) >= 3

    ids = [entry["id"] for entry in layout["anchors"]]
    assert ids.count("medieval_home") == 3
    assert ids.count("medieval_tower") == 1
    assert ids.count("medieval_bridge") == 1
    assert ids.count("forest_tree_round") >= 10
    assert ids.count("forest_tree_branching") >= 6
    assert ids.count("forest_bush") >= 12
    assert ids.count("forest_rock") >= 8


def test_rich_scene_builds_ground_paths_creek_and_dressing():
    scene = (
        ROOT
        / "godot"
        / "scenes"
        / "forest_village_50x50_rich_v0_2.tscn"
    ).read_text(encoding="utf-8")
    script = (
        ROOT
        / "godot"
        / "scripts"
        / "forest_village_50x50_rich.gd"
    ).read_text(encoding="utf-8")

    assert 'res://scenes/player.tscn' in scene
    assert 'res://scripts/camera_rig.gd' in scene
    assert "_build_ground_layers()" in script
    assert "_build_creek()" in script
    assert "_build_paths()" in script
    assert "_build_ground_dressing()" in script
    assert "_scatter_grass(" in script
    assert "_scatter_flower_clusters(" in script
    assert "_scatter_mushrooms(" in script
    assert "_build_garden(" in script
    assert "_paver(" in script
    assert "GoldenAnchorRuntime.instantiate_anchor" in script


def test_rich_ground_helpers_do_not_use_self_as_default_argument():
    script = (
        ROOT
        / "godot"
        / "scripts"
        / "forest_village_50x50_rich.gd"
    ).read_text(encoding="utf-8")

    assert "parent: Node3D = self" not in script
    assert "parent: Node3D = null" in script
