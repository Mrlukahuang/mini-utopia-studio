from studio.models.character import CharacterProfile
from studio.models.runtime_character import CharacterRuntimeSpec, RuntimeAnimationSpec
from studio.models.world import (
    CameraPoint,
    ChunkSpec,
    TourRoute,
    TourStep,
    WorldBlueprint,
    WorldPoint,
    WorldProfile,
)
from studio.runtime.three_world import THREE_VERSION, build_world_runtime_html, runtime_summary


def _blueprint() -> WorldBlueprint:
    return WorldBlueprint(
        location_asset_id="LOC_TEST",
        chunks=[
            ChunkSpec(chunk_x=x, chunk_z=z, generated=True, biome="meadow")
            for z in range(5)
            for x in range(5)
        ],
        camera_points=[
            CameraPoint(
                camera_id="CAM_ESTABLISHING",
                position=WorldPoint(x=4, y=11, z=10),
                look_at=WorldPoint(x=24, y=2, z=25),
                role="establishing",
            ),
            CameraPoint(
                camera_id="CAM_ENDING",
                position=WorldPoint(x=48, y=12, z=42),
                look_at=WorldPoint(x=28, y=1, z=25),
                role="ending",
            ),
        ],
        director_tours=[
            TourRoute(
                name="World Tour",
                steps=[
                    TourStep(camera_id="CAM_ESTABLISHING", movement="fly"),
                    TourStep(camera_id="CAM_ENDING", movement="cut"),
                ],
            )
        ],
    )


def test_runtime_summary_reads_saved_blueprint():
    profile = WorldProfile(
        world_name="Candy Cloud Valley",
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
    )
    summary = runtime_summary(profile=profile, blueprint=_blueprint())

    assert summary["grid"] == "50x50"
    assert summary["chunks"] == 25
    assert summary["camera_points"] == 2
    assert summary["director_tours"] == 1
    assert summary["theme_colors"][0] == "#F7B7D2"


def test_runtime_html_uses_pinned_threejs_and_blueprint_data():
    profile = WorldProfile(
        world_name="Candy Cloud Valley",
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
    )
    html = build_world_runtime_html(
        world_name="Candy Cloud Valley",
        profile=profile,
        blueprint=_blueprint(),
    )

    assert f"three@{THREE_VERSION}" in html
    assert "Candy Cloud Valley" in html
    assert '"chunk_x": 4' in html
    assert "KeyW" in html
    assert "ArrowUp" in html
    assert "Start Director Tour" in html
    assert "CAM_ESTABLISHING" in html
    assert "TorusGeometry" in html


def test_runtime_html_escapes_script_breakout_from_world_name():
    profile = WorldProfile(world_name="safe")
    html = build_world_runtime_html(
        world_name="</script><script>alert(1)</script>",
        profile=profile,
        blueprint=_blueprint(),
    )

    # Visible title is HTML escaped and serialized runtime JSON cannot close the module script.
    assert "&lt;/script&gt;" in html
    assert "\\u003c/script>" in html


def test_runtime_html_uses_character_profile_colors_and_modular_kit():
    profile = WorldProfile(
        world_name="Candy Cloud Valley",
        world_type="Cloud Village / 云端小镇",
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
    )
    character = CharacterProfile(
        favorite_color_hexes=["#F7B7D2", "#B9E7D0"],
        hair_or_fur_color_hex="#5B4036",
    )
    character.eyes.color_hex = "#7A5238"

    html = build_world_runtime_html(
        world_name="Candy Cloud Valley",
        profile=profile,
        blueprint=_blueprint(),
        character_name="Vivian",
        character_profile=character,
    )

    assert "Vivian" in html
    assert "#5B4036" in html
    assert "#7A5238" in html
    assert "addToyTree" in html
    assert "addToyHouse" in html
    assert "addToyRock" in html
    assert "addStarLamp" in html


def test_runtime_summary_exposes_character_identity_colors():
    profile = WorldProfile(theme_color_hexes=["#BDE3F7"])
    character = CharacterProfile(
        favorite_color_hexes=["#F7B7D2", "#B9E7D0"],
    )

    summary = runtime_summary(
        profile=profile,
        blueprint=_blueprint(),
        character_profile=character,
    )

    assert summary["character_colors"] == ["#F7B7D2", "#B9E7D0"]


def test_runtime_html_has_idle_walk_run_and_glb_loader_path():
    runtime = CharacterRuntimeSpec(
        mode="glb",
        model_data_uri="data:model/gltf-binary;base64,AAAA",
        animation_clips=RuntimeAnimationSpec(
            idle="Idle_Breath",
            walk="Walk_Cycle",
            run="Run_Cycle",
        ),
    )
    html = build_world_runtime_html(
        world_name="Candy Cloud Valley",
        profile=WorldProfile(theme_color_hexes=["#F7B7D2"]),
        blueprint=_blueprint(),
        character_name="Vivian",
        character_runtime=runtime,
    )

    assert "GLTFLoader" in html
    assert "AnimationMixer" in html
    assert "Idle_Breath" in html
    assert "Walk_Cycle" in html
    assert "Run_Cycle" in html
    assert "ShiftLeft" in html
    assert "setAnimationState" in html
    assert "updateProceduralAnimation" in html


def test_runtime_html_has_import_map_and_error_overlay():
    html = build_world_runtime_html(
        world_name="Candy Cloud Valley",
        profile=WorldProfile(theme_color_hexes=["#F7B7D2"]),
        blueprint=_blueprint(),
    )

    assert '<script type="importmap">' in html
    assert '"three": "https://cdn.jsdelivr.net/npm/three@' in html
    assert "three/addons/loaders/GLTFLoader.js" in html
    assert 'id="runtimeError"' in html
    assert "3D Runtime error:" in html


def test_runtime_html_has_floating_garden_world_identity_kit():
    profile = WorldProfile(
        world_name="Pastel Star Garden",
        world_type="Floating Islands / 漂浮岛",
        portal_form="Star Arch / 星星拱门",
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
    )
    blueprint = _blueprint()
    blueprint.portal.form = "Star Arch / 星星拱门" if blueprint.portal else "Star Arch / 星星拱门"

    html = build_world_runtime_html(
        world_name="Pastel Star Garden",
        profile=profile,
        blueprint=blueprint,
    )

    assert "floatingWorld" in html
    assert "addFlowerPatch" in html
    assert "addCloud" in html
    assert "CylinderGeometry" in html
    assert "ExtrudeGeometry" in html
    assert "portalForm.includes('star')" in html
    assert "(bp.paths || []).forEach" in html
