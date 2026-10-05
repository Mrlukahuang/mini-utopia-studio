import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_b_atlas_maps_match_real_pack_layouts():
    forest = json.loads(
        (
            ROOT
            / "assets"
            / "catalogs"
            / "atlas_maps"
            / "kaykit_forest_v0_1.json"
        ).read_text(encoding="utf-8")
    )
    medieval = json.loads(
        (
            ROOT
            / "assets"
            / "catalogs"
            / "atlas_maps"
            / "kaykit_medieval_v0_1.json"
        ).read_text(encoding="utf-8")
    )

    assert forest["layout"] == {"type": "horizontal_bands", "bands": 4}
    assert [item["slot"] for item in forest["regions"]] == [
        "foliage_base",
        "wood_base",
        "stone_base",
        "neutral_warm",
    ]

    assert medieval["layout"] == {"type": "grid", "rows": 4, "columns": 8}
    assert len(medieval["regions"]) == 4
    assert all(len(row) == 8 for row in medieval["regions"])


def test_candidate_b_bake_tool_is_source_preserving_and_profile_aware():
    text = (ROOT / "tools" / "bake_golden_palette.py").read_text(encoding="utf-8")

    assert "Source ZIPs and source-installed glTF/PNG files are never modified" in text
    assert "__{profile_id}" in text
    assert 'entry.setdefault("profile_res_paths", {})[args.profile]' in text
    assert '"kaykit_forest"' in text
    assert '"kaykit_medieval"' in text
    assert "gradient_strength=0.82" in text


def test_golden_runtime_can_request_palette_profile():
    runtime = (
        ROOT / "godot" / "scripts" / "golden_anchor_runtime.gd"
    ).read_text(encoding="utf-8")
    calibration = (
        ROOT / "godot" / "scripts" / "style_calibration_lab.gd"
    ).read_text(encoding="utf-8")
    compare = (
        ROOT / "godot" / "scripts" / "golden_palette_compare.gd"
    ).read_text(encoding="utf-8")

    assert 'profile_id: String = ""' in runtime
    assert 'entry.get("profile_res_paths", {})' in runtime
    assert 'profile_available("core_candidate_b")' in calibration
    assert '"core_candidate_b"' in calibration
    assert 'const PROFILE_ID := "core_candidate_b"' in compare
    assert '"SOURCE"' in compare
    assert '"CANDIDATE B"' in compare
