from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.world import (
    CameraPoint,
    LandmarkSpec,
    PathSpec,
    PortalSpec,
    WorldBlueprint,
    WorldLayoutElement,
    WorldPoint,
    ZoneSpec,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.world_concept_match_service import WorldConceptMatchService


def _world_with_blueprint(repo):
    blueprint = WorldBlueprint(
        layout_elements=[
            WorldLayoutElement(
                element_id="LAYOUT_PORTAL",
                name="Star Arch",
                kind="portal",
                position=WorldPoint(x=30, z=25),
                width=5,
                depth=3,
                height=6,
            ),
            WorldLayoutElement(
                element_id="LAYOUT_CASTLE",
                name="Moon Castle",
                kind="structure",
                position=WorldPoint(x=30, z=15),
                width=7,
                depth=7,
                height=8,
            ),
            WorldLayoutElement(
                element_id="LAYOUT_LAKE",
                name="Central Lake",
                kind="water",
                position=WorldPoint(x=25, z=25),
                width=12,
                depth=10,
                height=.3,
            ),
        ],
        portal=PortalSpec(position=WorldPoint(x=30, z=25), form="Star Arch"),
        landmarks=[
            LandmarkSpec(
                landmark_id="LANDMARK_01",
                name="Moon Castle",
                position=WorldPoint(x=30, z=15),
                kind="structure",
            )
        ],
        paths=[
            PathSpec(
                path_id="PATH_MAIN",
                points=[
                    WorldPoint(x=6, z=25),
                    WorldPoint(x=30, z=15),
                    WorldPoint(x=30, z=25),
                ],
            )
        ],
        zones=[
            ZoneSpec(
                zone_id="ZONE_PORTAL",
                name="Portal Area",
                kind="portal",
                min_x=26,
                max_x=34,
                min_z=21,
                max_z=29,
            ),
            ZoneSpec(
                zone_id="ZONE_WATER_01",
                name="Central Lake",
                kind="water",
                min_x=19,
                max_x=31,
                min_z=20,
                max_z=30,
            ),
        ],
        camera_points=[
            CameraPoint(
                camera_id="CAM_LANDMARK_01",
                position=WorldPoint(x=23, y=6, z=8),
                look_at=WorldPoint(x=30, z=15),
                role="landmark",
            ),
            CameraPoint(
                camera_id="CAM_PORTAL",
                position=WorldPoint(x=24, y=5, z=25),
                look_at=WorldPoint(x=30, z=25),
                role="portal_reveal",
            ),
        ],
    )
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Pastel Star Garden",
        slug="pastel-star-garden",
        metadata={
            "world_blueprint": blueprint.model_dump(mode="json"),
            "world_concept_path": "assets/LOC/concept.png",
        },
    )
    repo.save_asset(world)
    return world


def test_portal_correction_syncs_portal_zone_path_and_camera(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    world = _world_with_blueprint(repo)
    service = WorldConceptMatchService(repo)

    updated = service.apply_correction(
        location_asset_id=world.asset_id,
        element_id="LAYOUT_PORTAL",
        action="left",
    )

    portal_element = next(e for e in updated.layout_elements if e.element_id == "LAYOUT_PORTAL")
    assert portal_element.position.x == 26
    assert updated.portal is not None
    assert updated.portal.position.x == 26

    portal_zone = next(z for z in updated.zones if z.kind == "portal")
    assert portal_zone.min_x == 22
    assert portal_zone.max_x == 30
    assert updated.paths[0].points[-1].x == 26

    portal_cam = next(c for c in updated.camera_points if c.role == "portal_reveal")
    assert portal_cam.look_at.x == 26

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.metadata["world_concept_match_reviewed"] is True
    assert saved.metadata["world_concept_match_history"][-1]["action"] == "left"


def test_landmark_correction_syncs_landmark_path_and_camera(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    world = _world_with_blueprint(repo)
    service = WorldConceptMatchService(repo)

    updated = service.apply_correction(
        location_asset_id=world.asset_id,
        element_id="LAYOUT_CASTLE",
        action="back",
    )

    castle = next(l for l in updated.landmarks if l.name == "Moon Castle")
    assert castle.position.z == 11
    assert updated.paths[0].points[1].z == 11

    cam = next(c for c in updated.camera_points if c.role == "landmark")
    assert cam.look_at.z == 11


def test_water_resize_syncs_water_zone(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    world = _world_with_blueprint(repo)
    service = WorldConceptMatchService(repo)

    updated = service.apply_correction(
        location_asset_id=world.asset_id,
        element_id="LAYOUT_LAKE",
        action="bigger",
    )

    lake = next(e for e in updated.layout_elements if e.element_id == "LAYOUT_LAKE")
    water_zone = next(z for z in updated.zones if z.kind == "water")
    assert lake.width > 12
    assert lake.depth > 10
    assert water_zone.max_x - water_zone.min_x == lake.width
    assert water_zone.max_z - water_zone.min_z == lake.depth


def test_mark_reviewed_persists_review_gate(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    world = _world_with_blueprint(repo)
    service = WorldConceptMatchService(repo)

    service.mark_reviewed(location_asset_id=world.asset_id)

    saved = repo.get_asset(world.asset_id)
    assert saved is not None
    assert saved.metadata["world_concept_match_reviewed"] is True
    assert saved.metadata["world_concept_match_reviewed_at"]
