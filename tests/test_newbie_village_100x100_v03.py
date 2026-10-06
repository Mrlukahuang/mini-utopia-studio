from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "godot" / "scripts" / "newbie_village_100x100_v0_3.gd"
SCENE = ROOT / "godot" / "scenes" / "newbie_village_100x100_v0_3.tscn"
VAULT = ROOT / "godot" / "scripts" / "asset_vault_runtime.gd"
BASELINE = ROOT / "docs" / "WORLD_BASELINE_NEWBIE_VILLAGE_V1.md"


def test_v03_files_exist():
    assert SCRIPT.is_file()
    assert SCENE.is_file()


def test_v03_uses_box_fitted_block_bits_instead_of_guessing_asset_pivots():
    vault = VAULT.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    assert "instantiate_by_id_box_fit" in vault
    assert "_instantiate_entry_box_fit" in vault
    assert "best_entry_matching" in vault
    assert "target_size.x / bounds.size.x" in vault
    assert "target_size.y / bounds.size.y" in vault
    assert "target_size.z / bounds.size.z" in vault

    assert "AssetVaultRuntime.instantiate_by_id_box_fit" in script
    assert "_place_green_box_fit" in script
    assert "_place_yellow_box_fit" in script


def test_v03_ground_visual_and_collision_share_exact_y0_surface():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "the collider top and the visible Block Bits top are both exactly Y = 0" in text
    assert "Vector3(WORLD_SIZE, 0.60, WORLD_SIZE)" in text
    assert "GROUND_CAP_THICKNESS := 0.60" in text
    assert "Vector3(0.0, -0.30, 0.0)" in text


def test_v03_yellow_road_is_visible_above_green_ground():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "var road_bottom_y := 0.08 - ROAD_HEIGHT" in text
    assert "const MAIN_ROAD_WIDTH_BLOCKS := 3" in text
    assert "const BRANCH_ROAD_WIDTH_BLOCKS := 2" in text
    assert "MainRoadSolid" in text
    assert "BranchRoadNorthSolid" in text
    assert "BranchRoadSouthSolid" in text
    assert '["yellow"]' in text
    assert '["green"]' in text


def test_v03_house_bottom_uses_actual_block_pad_surface():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "var surface_y := _build_house_block_pad" in text
    assert "house_position := Vector3" in text
    assert "surface_y," in text
    assert "return surface_y" in text
    assert "HousePadCapCollision" in text
    assert "3x3 green Block Bits cap" in text


def test_v03_mountains_are_irregular_clusters_not_rectangular_ring_shelves():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "_build_irregular_layered_mountains" in text
    assert "_build_cliff_cluster" in text
    assert "wide_shape: Array[Vector2i]" in text
    assert "upper_shape: Array[Vector2i]" in text
    assert "peak_shape: Array[Vector2i]" in text
    assert "NorthWestUpper" in text
    assert "SouthEastPeak" in text
    assert "WestShelf" not in text
    assert "EastShelf" not in text


def test_v03_uses_forest_nature_to_soften_cliff_edges():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "_build_forest_reference_dressing" in text
    assert "Tree_1_A_Color1.gltf" in text
    assert "Rock_3_K_Color1.gltf" in text
    assert "Bush_4_C_Color1.gltf" in text
    assert "Grass_2_C_Color1.gltf" in text
    assert "Oversized Forest Nature rocks around cliff edges" in text


def test_v03_preserves_resource_yard_and_two_skeletons():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Wood_Log_Stack.gltf" in text
    assert "Stone_Chunks_Large.gltf" in text
    assert "const SKELETON_COUNT := 2" in text
    assert "Vector3(-44.0, 4.62, -10.0)" in text
    assert "Vector3(44.0, 4.42, 12.0)" in text


def test_v03_scene_and_baseline_point_to_current_builder():
    scene = SCENE.read_text(encoding="utf-8")
    baseline = BASELINE.read_text(encoding="utf-8")

    assert 'name="NewbieVillage100x100V03"' in scene
    assert 'res://scripts/newbie_village_100x100_v0_3.gd' in scene
    assert "newbie_village_100x100_v0_3.tscn" in baseline
    assert "Asset pivots must never be guessed" in baseline
