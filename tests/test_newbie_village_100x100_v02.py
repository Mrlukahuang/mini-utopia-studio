from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "godot" / "scripts" / "newbie_village_100x100_v0_2.gd"
SCENE = ROOT / "godot" / "scenes" / "newbie_village_100x100_v0_2.tscn"
BASELINE = ROOT / "docs" / "WORLD_BASELINE_NEWBIE_VILLAGE_V1.md"


def test_v02_scene_and_script_exist():
    assert SCRIPT.is_file()
    assert SCENE.is_file()


def test_v02_uses_plain_yellow_and_green_block_bits_searches():
    text = SCRIPT.read_text(encoding="utf-8")

    assert '["block", "yellow"]' in text
    assert '["block", "green"]' in text
    assert "yellow_block_asset_id" in text
    assert "green_block_asset_id" in text
    assert '["dirt"]' not in text
    assert '["soil"]' not in text


def test_v02_keeps_locked_road_hierarchy():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "const MAIN_ROAD_WIDTH_BLOCKS := 3" in text
    assert "const BRANCH_ROAD_WIDTH_BLOCKS := 2" in text
    assert "One north-south main road" in text
    assert "Two east-west branch roads" in text
    assert "MainRoadSolid" in text
    assert "BranchRoadNorthSolid" in text
    assert "BranchRoadSouthSolid" in text


def test_v02_has_green_block_floor_and_house_pads():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "_build_green_block_valley" in text
    assert "_place_green_surface_block" in text
    assert "_build_house_pad" in text
    assert "HousePadCore" in text
    assert "_build_pad_steps" in text


def test_v02_has_two_additional_mountain_elevation_bands():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Level 2: the additional mountain shelf" in text
    assert "Level 3: two compact peaks" in text
    assert "NorthWestUpper" in text
    assert "SouthEastUpper" in text
    assert "NorthWestPeak" in text
    assert "SouthEastPeak" in text


def test_v02_uses_forest_nature_and_resource_bits_content():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Tree_1_A_Color1.gltf" in text
    assert "Rock_3_K_Color1.gltf" in text
    assert "Bush_4_C_Color1.gltf" in text
    assert "Grass_2_C_Color1.gltf" in text
    assert "Wood_Log_Stack.gltf" in text
    assert "Stone_Chunks_Large.gltf" in text


def test_v02_keeps_larger_houses_and_two_scattered_skeletons():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "const HOUSE_TARGET_HEIGHT := 4.8" in text
    assert "const SKELETON_COUNT := 2" in text
    assert "Vector3(-41.0, 4.15, -18.0)" in text
    assert "Vector3(41.0, 4.55, 20.0)" in text
    assert "_spawn_house_on_pad" in text


def test_v02_scene_uses_new_builder_and_southern_spawn():
    text = SCENE.read_text(encoding="utf-8")

    assert 'name="NewbieVillage100x100V02"' in text
    assert 'res://scripts/newbie_village_100x100_v0_2.gd' in text
    assert 'position = Vector3(0, 0.9, 34)' in text


def test_baseline_now_locks_yellow_roads_green_ground_and_extra_levels():
    text = BASELINE.read_text(encoding="utf-8")

    assert "plain yellow KayKit Block Bits cube" in text
    assert "plain green KayKit Block Bits cube" in text
    assert "at least two additional elevation bands" in text
    # v0.2 remains a valid historical smoke-test scene even when the
    # baseline advances to a newer current scene.
    assert "newbie_village_100x100_v0_2.tscn" in (
        ROOT / "godot" / "scenes" / "newbie_village_100x100_v0_2.tscn"
    ).as_posix()
