import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mountain_town_world_kit_contains_real_kaykit_roads_rivers_and_resources():
    catalog = json.loads(
        (ROOT / "assets" / "catalogs" / "mountain_town_world_kit_v1.json").read_text(
            encoding="utf-8"
        )
    )
    ids = {entry["id"] for entry in catalog["assets"]}

    assert len(catalog["assets"]) == 87
    assert "med_hex_grass" in ids
    assert "med_hex_road_A" in ids
    assert "med_hex_road_L" in ids
    assert "med_hex_road_A_sloped_high" in ids
    assert "med_hex_river_A" in ids
    assert "med_hex_river_crossing_A" in ids
    assert "med_building_bridge_A" in ids
    assert "med_mountain_A_grass_trees" in ids
    assert "forest_grass_1_a_color1" in ids
    assert "resource_wood_log_stack" in ids
    assert "resource_stone_bricks_stack_medium" in ids


def test_mountain_town_layout_has_30_real_buildings_and_multi_level_world():
    data = json.loads(
        (
            ROOT
            / "godot"
            / "config"
            / "worlds"
            / "mountain_town_50x50_v0_3.json"
        ).read_text(encoding="utf-8")
    )

    assert data["world_id"] == "mountain_town_50x50_v03"
    assert data["grid"] == {"columns": 10, "rows": 12, "tile_scale": 2.3}
    assert data["profile_id"] == "core_candidate_b"
    assert len(data["buildings"]) == 30
    assert len(data["road_cells"]) >= 20
    assert len(data["mountains"]) >= 7
    assert len(data["resources"]) >= 6
    assert any(entry.get("level") == 1 for entry in data["buildings"])
    assert any(entry.get("slope") is True for entry in data["road_cells"])


def test_mountain_town_scene_uses_real_worldkit_runtime_not_procedural_roads():
    script = (
        ROOT / "godot" / "scripts" / "mountain_town_50x50.gd"
    ).read_text(encoding="utf-8")
    scene = (
        ROOT / "godot" / "scenes" / "mountain_town_50x50_v0_3.tscn"
    ).read_text(encoding="utf-8")

    assert "WorldKitRuntime.instantiate_asset" in script
    assert '"med_hex_grass"' in script
    assert '"med_hex_river_crossing_A"' in script
    assert '"med_building_bridge_A"' in script
    assert "_build_mountain_ring()" in script
    assert "_build_resource_yards()" in script
    assert "_build_forest_dressing()" in script
    assert "_add_hill_access_ramp" in script
    assert "res://scenes/player.tscn" in scene
    assert "res://scripts/camera_rig.gd" in scene


def test_mountain_town_preparation_is_one_command_and_source_preserving():
    text = (
        ROOT / "tools" / "prepare_mountain_town_assets.py"
    ).read_text(encoding="utf-8")

    assert "python3 tools/prepare_mountain_town_assets.py" in text
    assert "source archives" in text.lower()
    assert "profile_res_paths" in text
    assert "CATALOG_PATH" in text
    assert 'catalog["packs"]' in text
    assert 'catalog["assets"]' in text


def test_block_bits_are_not_used_as_visible_primary_terrain():
    catalog = json.loads(
        (ROOT / "assets" / "catalogs" / "mountain_town_world_kit_v1.json").read_text(
            encoding="utf-8"
        )
    )
    packs = {entry["pack"] for entry in catalog["assets"]}

    # The visible terrain language is Medieval Hexagon + Forest Nature.
    # Block Bits remains a utility fallback to avoid voxel drift.
    assert "kaykit_medieval" in packs
    assert "kaykit_forest" in packs
    assert "kaykit_resource" in packs
    assert "kaykit_blockbits" not in packs
