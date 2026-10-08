from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENES = ROOT / "godot" / "scenes"


def test_active_godot_scene_folder_stays_small_and_current():
    assert {path.name for path in SCENES.glob("*.tscn")} == {
        "main.tscn",
        "player.tscn",
        "newbie_village_100x100_v0_3.tscn",
        "avatar_contract_smoke_test.tscn",
        "equipment_runtime_smoke_test.tscn",
        "director_stage.tscn",
        "character_creator.tscn",
    }


def test_legacy_scene_names_do_not_return_to_active_folder():
    legacy_prefixes = (
        "forest_village_50x50",
        "mountain_town_50x50",
        "green_terraced_mountain_town",
        "storybook_terraced_town",
        "newbie_village_100x100_v0_1",
        "newbie_village_100x100_v0_2",
        "golden_anchor_lineup",
        "golden_palette_compare",
        "style_calibration_lab",
    )
    current_names = [path.name for path in SCENES.glob("*.tscn")]
    for prefix in legacy_prefixes:
        assert not any(name.startswith(prefix) for name in current_names)
