from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "godot" / "scripts" / "newbie_village_100x100.gd"
SCENE = ROOT / "godot" / "scenes" / "newbie_village_100x100_v0_1.tscn"
BASELINE = ROOT / "docs" / "WORLD_BASELINE_NEWBIE_VILLAGE_V1.md"
VAULT_RUNTIME = ROOT / "godot" / "scripts" / "asset_vault_runtime.gd"


def test_newbie_village_baseline_files_exist():
    assert SCRIPT.is_file()
    assert SCENE.is_file()
    assert BASELINE.is_file()


def test_newbie_village_locks_100x100_and_simple_road_hierarchy():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "const WORLD_SIZE := 100.0" in text
    assert "const MAIN_ROAD_WIDTH_BLOCKS := 3" in text
    assert "const BRANCH_ROAD_WIDTH_BLOCKS := 2" in text
    assert "one N-S main road plus two E-W branch roads" in text
    assert "hex_" not in text


def test_newbie_village_uses_requested_asset_families():
    text = SCRIPT.read_text(encoding="utf-8")

    assert '["block"]' in text
    assert '["dirt"]' in text
    assert "Tree_1_A_Color1.gltf" in text
    assert "Rock_3_K_Color1.gltf" in text
    assert "Wood_Log_Stack.gltf" in text
    assert "Stone_Chunks_Large.gltf" in text
    assert '["skeleton"]' in text


def test_newbie_village_has_many_larger_houses_and_two_skeletons():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "const HOUSE_TARGET_HEIGHT := 4.8" in text
    assert "const SKELETON_COUNT := 2" in text
    assert "building_home_A_red.gltf" in text
    assert "building_home_B_blue.gltf" in text
    assert "building_tavern_red.gltf" in text
    assert "building_church_red.gltf" in text
    assert "for index in range(SKELETON_COUNT)" in text


def test_newbie_village_has_solid_collision_baseline():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "_add_solid_box" in text
    assert "_add_collision_box_only" in text
    assert "BuildingCollision" in text
    assert "BoundaryWest" in text
    assert "BoundaryEast" in text
    assert "BoundaryNorth" in text
    assert "BoundarySouth" in text


def test_scene_is_named_newbie_village_and_uses_builder():
    text = SCENE.read_text(encoding="utf-8")

    assert 'name="NewbieVillage100x100V01"' in text
    assert 'res://scripts/newbie_village_100x100.gd' in text
    assert 'position = Vector3(0, 0.9, 41)' in text


def test_asset_vault_runtime_supports_pack_matching_and_fit_height():
    text = VAULT_RUNTIME.read_text(encoding="utf-8")

    assert "first_entry_matching" in text
    assert "instantiate_first_matching" in text
    assert "target_height: float = 0.0" in text
    assert "_bounds_in_root" in text


def test_baseline_explicitly_forbids_hex_terrain():
    text = BASELINE.read_text(encoding="utf-8")

    assert "NO hex / honeycomb terrain" in text
    assert "3 blocks wide" in text
    assert "2 blocks wide" in text
    assert "36+ road-oriented buildings" in text
    assert "Exactly **2 skeleton soldiers**" in text
