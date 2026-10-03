from studio.models.world import (
    BLUEPRINT_SCHEMA_VERSION,
    GridSpec,
    WorldBlueprint,
    WorldProfile,
)


def test_default_world_blueprint_is_50_by_50_with_25_chunks_expected():
    blueprint = WorldBlueprint()
    assert blueprint.grid.width == 50
    assert blueprint.grid.depth == 50
    assert blueprint.grid.chunk_width == 10
    assert blueprint.grid.chunk_depth == 10
    assert blueprint.expected_chunk_count() == 25


def test_world_has_four_open_expansion_edges_by_default():
    blueprint = WorldBlueprint()
    assert {edge.edge for edge in blueprint.expansion_edges} == {
        "north",
        "south",
        "east",
        "west",
    }
    assert all(edge.open_for_growth for edge in blueprint.expansion_edges)


def test_world_profile_is_playable_and_keeps_theme_colors_separate_from_style_canon():
    profile = WorldProfile(
        world_name="Candy Cloud Valley",
        theme_color_hexes=["#F7B7D2", "#B9E7D0"],
    )
    assert profile.playable is True
    assert profile.world_name == "Candy Cloud Valley"
    assert profile.theme_color_hexes == ["#F7B7D2", "#B9E7D0"]


def test_blueprint_schema_version_is_explicit():
    assert BLUEPRINT_SCHEMA_VERSION == "0.3"


def test_structural_blueprint_contains_paths_zones_and_director_tour():
    from studio.services.world_blueprint_service import WorldBlueprintService

    profile = WorldProfile(
        world_name="Candy Cloud Valley",
        world_type="Cloud Village / 云端小镇",
        terrain=["Floating Land / 漂浮陆地"],
        landmark_ideas=["Star Tower / 星星塔"],
        portal_form="Star Arch / 星星拱门",
    )
    blueprint = WorldBlueprintService().build(
        location_asset_id="LOC_TEST",
        style_asset_id="STYLE_TEST",
        profile=profile,
        concept_path="assets/LOC_TEST/concept.png",
        concept_direction="dream",
    )

    assert len(blueprint.chunks) == 25
    assert blueprint.spawn.x == 6
    assert blueprint.portal is not None
    assert blueprint.paths[0].path_id == "PATH_MAIN"
    assert "ZONE_CORE" in blueprint.walkable_zone_ids
    assert blueprint.camera_points
    assert blueprint.director_tours


def test_blueprint_visual_anchor_preserves_world_identity():
    from studio.services.world_blueprint_service import WorldBlueprintService

    profile = WorldProfile(
        world_name="Pastel Star Garden",
        world_type="Floating Islands / 漂浮岛",
        portal_form="Star Arch / 星星拱门",
        landmark_ideas=["Moon Castle / 月亮城堡"],
        water_features=["Central Lake / 中央湖"],
        landscape_elements=["Pink Forest / 粉色树林"],
        surprise_elements=["Rainbow Waterfall / 彩虹瀑布"],
        mood=["Dreamy / 梦幻"],
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
    )

    blueprint = WorldBlueprintService().build(
        location_asset_id="LOC_TEST",
        style_asset_id="STYLE_TEST",
        profile=profile,
        concept_path="assets/LOC_TEST/concept/playable.png",
        concept_direction="playable",
    )

    anchor = blueprint.visual_anchor
    assert anchor.extraction_method == "deterministic_profile_v1"
    assert anchor.concept_direction == "playable"
    assert anchor.concept_path.endswith("playable.png")
    assert "Floating Islands / 漂浮岛" in anchor.must_preserve
    assert "Star Arch / 星星拱门" in anchor.must_preserve
    assert "Moon Castle / 月亮城堡" in anchor.must_preserve
    assert "Central Lake / 中央湖" in anchor.must_preserve
    assert "Pink Forest / 粉色树林" in anchor.must_preserve
    assert "Rainbow Waterfall / 彩虹瀑布" in anchor.flexible_details
    assert anchor.palette_hexes == ["#F7B7D2", "#B9E7D0", "#D7C2F3"]
