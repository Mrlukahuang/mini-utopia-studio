from studio.models.character import CharacterProfile
from studio.models.runtime_character import CharacterRuntimeSpec, RuntimeAnimationSpec
from studio.models.world import (
    CameraPoint,
    ChunkSpec,
    TourRoute,
    TourStep,
    PortalSpec,
    WorldBlueprint,
    WorldLayoutElement,
    WorldPoint,
    WorldProfile,
    WorldVisualAnchor,
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
    blueprint.portal = PortalSpec(
        position=WorldPoint(x=25, y=0, z=25),
        form="Star Arch / 星星拱门",
    )

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


def test_runtime_consumes_visual_anchor_hints():
    blueprint = _blueprint()
    blueprint.visual_anchor = WorldVisualAnchor(
        must_preserve=[
            "Floating Islands / 漂浮岛",
            "Star Arch / 星星拱门",
            "Pink Garden / 粉色花园",
        ],
        concept_summary="floating pastel garden with star portal",
    )
    blueprint.portal = PortalSpec(
        position=WorldPoint(x=25, y=0, z=25),
        form="",
    )

    html = build_world_runtime_html(
        world_name="Anchor Driven World",
        profile=WorldProfile(world_name="Anchor Driven World"),
        blueprint=blueprint,
    )

    assert "anchorText" in html
    assert "anchorText.includes('floating')" in html
    assert "anchorText.includes('garden')" in html
    assert "visualAnchor.must_preserve" in html


def test_runtime_renders_compiled_layout_water_and_concept_palette():
    blueprint = _blueprint()
    blueprint.visual_anchor.palette_hexes = ["#AABBCC", "#DDEEFF"]
    blueprint.layout_elements = [
        WorldLayoutElement(
            element_id="LAYOUT_01",
            name="Central Lake",
            kind="water",
            position=WorldPoint(x=25, y=0, z=25),
            width=12,
            depth=8,
            height=.3,
        )
    ]

    html = build_world_runtime_html(
        world_name="Layout World",
        profile=WorldProfile(theme_color_hexes=["#111111"]),
        blueprint=blueprint,
    )

    assert "#AABBCC" in html
    assert "(bp.layout_elements || []).forEach" in html
    assert "element.kind === 'water'" in html
    assert "CylinderGeometry" in html


def test_runtime_html_has_zoom_wheel_and_blueprint_aware_overview_camera():
    blueprint = _blueprint()
    blueprint.layout_elements = [
        WorldLayoutElement(
            element_id="SCENE_AERIAL",
            name="Aerial Landmark",
            kind="landmark",
            spatial_mode="aerial",
            elevation="high",
            geometry_role="organic",
            position=WorldPoint(x=40, y=22, z=40),
            width=10,
            depth=7,
            height=8,
        )
    ]

    html = build_world_runtime_html(
        world_name="Vertical World",
        profile=WorldProfile(world_name="Vertical World"),
        blueprint=blueprint,
    )

    assert 'id="zoomOut"' in html
    assert 'id="zoomIn"' in html
    assert 'id="overview"' in html
    assert 'id="zoomState"' in html
    assert "renderer.domElement.addEventListener('wheel'" in html
    assert "const layoutTopY = Math.max" in html
    assert "const worldTopY = Math.max" in html
    assert "const overviewTarget = new THREE.Vector3" in html
    assert "function showOverview()" in html
    assert "overviewMode = false" in html
    assert "baseFollowOffset" in html
    assert "multiplyScalar(followZoom)" in html
    assert "Mouse Wheel / 滚轮缩放" in html


def test_runtime_semantic_proxy_uses_layout_and_hides_ground_quilt_for_floating_terrain():
    blueprint = _blueprint()
    blueprint.layout_elements = [
        WorldLayoutElement(
            element_id="SCENE_ISLAND",
            name="Cloud Island",
            kind="terrain",
            spatial_mode="floating",
            elevation="medium",
            geometry_role="terrain_mass",
            traversability="walkable",
            position=WorldPoint(x=25, y=8, z=25),
            width=12,
            depth=10,
            height=4,
        ),
        WorldLayoutElement(
            element_id="SCENE_CARRIER",
            name="Gentle Sky Carrier",
            kind="landmark",
            spatial_mode="aerial",
            elevation="high",
            geometry_role="volume",
            traversability="scenic",
            position=WorldPoint(x=40, y=16, z=40),
            width=12,
            depth=7,
            height=7,
        ),
        WorldLayoutElement(
            element_id="SCENE_PLATFORM",
            name="Back Garden Station",
            kind="structure",
            spatial_mode="elevated",
            elevation="high",
            geometry_role="platform",
            traversability="walkable",
            position=WorldPoint(x=40, y=22, z=40),
            width=9,
            depth=7,
            height=2,
        ),
    ]

    html = build_world_runtime_html(
        world_name="Semantic Sky World",
        profile=WorldProfile(world_name="Semantic Sky World"),
        blueprint=blueprint,
    )

    assert "const semanticElevatedTerrain" in html
    assert "if (!semanticElevatedTerrain)" in html
    assert "function addSemanticElement" in html
    assert "function addSemanticLabel" in html
    assert "Generic soft-body proxy for organic subjects and legacy aerial volume" in html
    assert "role === 'organic'" in html
    assert "element.kind === 'landmark'" in html
    assert "['floating','aerial','suspended'].includes(spatialMode)" in html
    assert "compiledElementIds" in html
    assert "if (!compiledElementIds.has(element.element_id)) addSemanticElement" in html
    assert "if (!(bp.layout_elements || []).length)" in html
    assert "Gentle Sky Carrier" in html
    assert "Back Garden Station" in html


def test_runtime_semantic_proxy_labels_main_portal():
    blueprint = _blueprint()
    blueprint.portal = PortalSpec(
        position=WorldPoint(x=25, y=14, z=25),
        form="Moon Star Portal",
    )
    html = build_world_runtime_html(
        world_name="Portal Label World",
        profile=WorldProfile(world_name="Portal Label World"),
        blueprint=blueprint,
    )

    assert "addSemanticLabel(" in html
    assert "bp.portal.form || profile.portal_form || 'Portal'" in html
