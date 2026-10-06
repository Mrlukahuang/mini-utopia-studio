import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = (
    ROOT
    / "godot"
    / "config"
    / "worlds"
    / "storybook_terraced_town_50x50_v0_5.json"
)


def _load_vault_module():
    path = ROOT / "tools" / "install_full_asset_vault.py"
    spec = importlib.util.spec_from_file_location(
        "install_full_asset_vault_test_module",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asset_vault_extracts_gltf_and_direct_dependencies(tmp_path):
    module = _load_vault_module()
    module.GODOT_ROOT = tmp_path / "godot"
    module.VAULT_ROOT = (
        module.GODOT_ROOT / "assets" / "external" / "library"
    )

    archive = tmp_path / "KayKit_Test_Pack.zip"
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"uri": "model.bin", "byteLength": 4}],
        "images": [{"uri": "texture.png"}],
    }

    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "KayKit_Test_Pack/Assets/gltf/model.gltf",
            json.dumps(gltf),
        )
        zf.writestr(
            "KayKit_Test_Pack/Assets/gltf/model.bin",
            b"1234",
        )
        zf.writestr(
            "KayKit_Test_Pack/Assets/gltf/texture.png",
            b"png",
        )
        zf.writestr(
            "KayKit_Test_Pack/License.txt",
            "CC0",
        )

    result = module.install_archive(archive, "fakehash")

    assert result["asset_count"] == 1
    entry = result["assets"][0]
    installed = module.GODOT_ROOT / entry["res_path"].removeprefix("res://")
    assert installed.is_file()
    assert (installed.parent / "model.bin").is_file()
    assert (installed.parent / "texture.png").is_file()
    assert result["license_files"]


def test_asset_vault_is_incremental_and_pack_scoped():
    text = (
        ROOT / "tools" / "install_full_asset_vault.py"
    ).read_text(encoding="utf-8")

    assert 'DEFAULT_NAME_HINTS = ("kaykit", "kenney", "quaternius", "megakit")' in text
    assert "archive_sha256" in text
    assert 'previous_pack.get("sha256") == digest' in text
    assert "Reused unchanged packs" in text
    assert "SUPPORTED_EXTENSIONS = {".gltf", ".glb"}" in text


def test_v05_has_one_horizontal_avenue_and_two_vertical_side_streets():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    main = data["main_road"]
    assert len(main) == 8
    assert len({row for _col, row in main}) == 1
    assert [col for col, _row in main] == list(range(1, 9))

    sides = data["side_roads"]
    assert len(sides) == 2
    assert all(len(path) == 10 for path in sides)
    assert {path[0][0] for path in sides} == {3, 7}
    for path in sides:
        assert len({col for col, _row in path}) == 1
        assert [row for _col, row in path] == list(range(1, 11))


def test_v05_has_30_street_facing_buildings_and_two_river_crossings():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert len(data["buildings"]) == 30
    assert all(entry["face_road"] for entry in data["buildings"])
    assert data["river"]["crossing_cols"] == [3, 7]
    assert any(entry["r"] == 1 for entry in data["buildings"])


def test_v05_scene_uses_layered_terrain_and_no_separate_bridge():
    script = (
        ROOT
        / "godot"
        / "scripts"
        / "storybook_terraced_town_50x50.gd"
    ).read_text(encoding="utf-8")

    assert '"med_hex_grass_bottom"' in script
    assert "crossing_cols" in script
    assert '"med_hex_river_crossing_A"' in script
    assert "med_building_bridge_A" not in script
    assert "med_building_bridge_B" not in script
    assert "return 2" in script
    assert "1 horizontal avenue + 2 side streets" in script


def test_asset_vault_runtime_can_search_by_id_and_filename():
    text = (
        ROOT / "godot" / "scripts" / "asset_vault_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "class_name AssetVaultRuntime" in text
    assert "entry_by_id" in text
    assert "entries_by_filename" in text
    assert "instantiate_by_id" in text
    assert "instantiate_first_filename" in text
