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
    assert BLUEPRINT_SCHEMA_VERSION == "0.2"


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
