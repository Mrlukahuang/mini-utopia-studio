import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_golden_anchor_verdicts_cover_installed_manifest():
    installed = json.loads(
        (ROOT / "assets" / "catalogs" / "golden_style_anchors_v1.json").read_text(
            encoding="utf-8"
        )
    )
    verdicts = json.loads(
        (ROOT / "assets" / "catalogs" / "golden_style_anchor_verdicts_v1.json").read_text(
            encoding="utf-8"
        )
    )

    installed_ids = {entry["id"] for entry in installed["anchors"]}
    verdict_ids = set(verdicts["verdicts"])

    assert installed_ids == verdict_ids


def test_only_approved_style_anchors_feed_style_sheet():
    verdicts = json.loads(
        (ROOT / "assets" / "catalogs" / "golden_style_anchor_verdicts_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert verdicts["style_sheet_include"] == [
        "forest_tree_round",
        "medieval_home",
        "medieval_tower",
        "adventurer_knight",
    ]
    for anchor_id in verdicts["style_sheet_include"]:
        assert verdicts["verdicts"][anchor_id]["status"] == "style_anchor"

    assert verdicts["verdicts"]["platformer_platform"]["status"] == "gameplay_utility"
    assert verdicts["verdicts"]["platformer_slope"]["status"] == "gameplay_utility"
    assert verdicts["verdicts"]["kenney_castle_tower"]["status"] == "conditional"


def test_candidate_b_semantic_profile_covers_all_static_slots():
    slots = json.loads(
        (ROOT / "godot" / "config" / "style" / "semantic_slots_v0_1.json").read_text(
            encoding="utf-8"
        )
    )
    profile = json.loads(
        (
            ROOT
            / "godot"
            / "config"
            / "style"
            / "profiles"
            / "core_candidate_b_v0_1.json"
        ).read_text(encoding="utf-8")
    )

    assert set(profile["slot_to_palette_key"]) == set(slots["slots"])
    assert profile["slot_to_palette_key"]["foliage_light"] == "mint"
    assert profile["slot_to_palette_key"]["foliage_base"] == "sage"
    assert profile["slot_to_palette_key"]["foliage_dark"] == "moss"
