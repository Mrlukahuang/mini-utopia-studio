import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = (
    ROOT
    / "godot"
    / "config"
    / "worlds"
    / "green_terraced_mountain_town_50x50_v0_4.json"
)


def _neighbors(c: int, r: int):
    if r % 2 == 0:
        offsets = [(1, 0), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1)]
    else:
        offsets = [(1, 0), (1, 1), (0, 1), (-1, 0), (0, -1), (1, -1)]
    return {(c + dc, r + dr) for dc, dr in offsets}


def test_green_terrain_map_fixes_medieval_grass_swatch():
    mapping = json.loads(
        (
            ROOT
            / "assets"
            / "catalogs"
            / "atlas_maps"
            / "kaykit_medieval_green_terrain_v0_1.json"
        ).read_text(encoding="utf-8")
    )

    assert mapping["profile_id"] == "core_candidate_b_green_terrain"
    assert mapping["regions"][2][0] == "foliage_base"
    assert mapping["regions"][1][1] == "water_base"
    assert mapping["regions"][2][3] == "neutral_warm"


def test_v04_has_one_main_road_and_exactly_four_winding_side_roads():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert len(data["main_road"]) >= 10
    assert len(data["side_roads"]) == 4
    assert all(len(path) >= 5 for path in data["side_roads"])

    for path in [data["main_road"], *data["side_roads"]]:
        for current, nxt in zip(path, path[1:]):
            assert tuple(nxt) in _neighbors(*current), (current, nxt)


def test_v04_has_30_street_facing_buildings_and_hill_houses():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert len(data["buildings"]) == 30
    assert all(entry["face_road"] for entry in data["buildings"])
    assert any(entry["r"] <= 2 for entry in data["buildings"])
    assert any(entry["c"] in {1, 8, 9} for entry in data["buildings"])


def test_v04_uses_river_crossing_tile_and_no_floating_bridge_building():
    script = (
        ROOT
        / "godot"
        / "scripts"
        / "green_terraced_mountain_town_50x50.gd"
    ).read_text(encoding="utf-8")

    assert '"med_hex_river_crossing_A"' in script
    assert "med_building_bridge_A" not in script
    assert "med_building_bridge_B" not in script
    assert "_build_bridge()" not in script


def test_v04_builds_layered_terraces_and_real_forest_dressing():
    script = (
        ROOT
        / "godot"
        / "scripts"
        / "green_terraced_mountain_town_50x50.gd"
    ).read_text(encoding="utf-8")

    assert '"med_hex_grass_bottom"' in script
    assert "_build_terrain_stack(" in script
    assert '"forest_grass_1_a_color1"' in script
    assert '"forest_bush_4_a_color1"' in script
    assert '"forest_rock_3_n_color1"' in script
    assert '"forest_tree_2_e_color1"' in script
    assert "_yaw_toward_nearest_road" in script


def test_prepare_script_bakes_core_and_green_terrain_profiles():
    text = (
        ROOT / "tools" / "prepare_mountain_town_assets.py"
    ).read_text(encoding="utf-8")

    assert 'CORE_PROFILE_ID = "core_candidate_b"' in text
    assert 'GREEN_TERRAIN_PROFILE_ID = "core_candidate_b_green_terrain"' in text
    assert "GREEN_TERRAIN_MAP" in text
    assert "green_categories" in text


def test_world_kit_expands_real_forest_nature_variants():
    catalog = json.loads(
        (
            ROOT / "assets" / "catalogs" / "mountain_town_world_kit_v1.json"
        ).read_text(encoding="utf-8")
    )
    ids = {entry["id"] for entry in catalog["assets"]}

    assert len(catalog["assets"]) >= 100
    assert "forest_grass_1_a_singlesided_color1" in ids
    assert "forest_bush_4_a_color1" in ids
    assert "forest_rock_3_n_color1" in ids
    assert "forest_tree_2_e_color1" in ids
