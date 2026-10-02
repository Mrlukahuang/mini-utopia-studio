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
