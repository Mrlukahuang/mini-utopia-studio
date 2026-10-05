import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANCHORS_PATH = ROOT / "assets" / "catalogs" / "golden_style_anchors_v1.json"


def test_golden_style_anchor_manifest_is_small_curated_and_unique():
    data = json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))
    anchors = data["anchors"]

    assert data["schema_version"] == "1.0"
    assert len(anchors) == 13
    assert len({entry["id"] for entry in anchors}) == len(anchors)
    assert {entry["pack"] for entry in anchors} == {
        "kaykit_forest",
        "kaykit_medieval",
        "kaykit_platformer",
        "kaykit_dungeon",
        "kaykit_adventurers",
        "kaykit_skeletons",
        "kenney_castle",
    }
    assert all(entry["source_member"].lower().endswith((".gltf", ".glb")) for entry in anchors)


def test_golden_anchor_lineup_has_required_style_categories():
    data = json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))
    categories = {entry["category"] for entry in data["anchors"]}

    assert {
        "nature",
        "architecture",
        "gameplay",
        "prop",
        "character",
        "creature",
        "compatibility",
    }.issubset(categories)


def test_golden_anchor_installer_preserves_local_source_archives():
    installer = (ROOT / "tools" / "install_golden_anchors.py").read_text(
        encoding="utf-8"
    )

    assert "zipfile.ZipFile" in installer
    assert "installed_manifest.json" in installer
    assert "source archives remain immutable" in installer.lower()
    assert "shutil.rmtree(install_root)" in installer
    assert "archive_path" in installer


def test_godot_golden_anchor_runtime_and_scenes_are_wired():
    runtime = (ROOT / "godot" / "scripts" / "golden_anchor_runtime.gd").read_text(
        encoding="utf-8"
    )
    calibration = (
        ROOT / "godot" / "scripts" / "style_calibration_lab.gd"
    ).read_text(encoding="utf-8")
    lineup = (
        ROOT / "godot" / "scripts" / "golden_anchor_lineup.gd"
    ).read_text(encoding="utf-8")

    assert "installed_manifest.json" in runtime
    assert "instantiate_anchor" in runtime
    assert '"medieval_home"' in calibration
    assert '"forest_tree_round"' in calibration
    assert '"adventurer_knight"' in calibration
    assert "GoldenAnchorRuntime.has_installed()" in calibration
    assert '"kenney_castle_tower"' in lineup


def test_locally_extracted_golden_binaries_are_ignored():
    ignore = (ROOT / "godot" / ".gitignore").read_text(encoding="utf-8")

    assert "assets/external/golden/*" in ignore
    assert "!assets/external/golden/README.md" in ignore
