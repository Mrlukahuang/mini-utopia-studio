from __future__ import annotations

from studio.models.world import (
    CameraPoint,
    ChunkSpec,
    GridSpec,
    LandmarkSpec,
    PathSpec,
    PortalSpec,
    SpawnPoint,
    TourRoute,
    TourStep,
    WorldBlueprint,
    WorldPoint,
    WorldProfile,
    ZoneSpec,
)
from studio.services.world_visual_anchor_service import WorldVisualAnchorService
from studio.services.world_layout_service import WorldLayoutService


class WorldBlueprintService:
    """Build deterministic executable World Blueprints.

    Blueprint-first planning is the primary World Factory path. Image-driven
    builds remain available for the optional legacy / Image-to-World path.
    """

    def __init__(
        self,
        visual_anchor_service: WorldVisualAnchorService | None = None,
        layout_service: WorldLayoutService | None = None,
    ):
        self.visual_anchor_service = visual_anchor_service or WorldVisualAnchorService()
        self.layout_service = layout_service or WorldLayoutService()

    def plan(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
        profile: WorldProfile,
    ) -> WorldBlueprint:
        """Plan the playable world directly from creator intent, before imagery."""
        return self.build(
            location_asset_id=location_asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            concept_path="",
            concept_direction="blueprint_first",
            concept_image_bytes=None,
        )

    def build(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
        profile: WorldProfile,
        concept_path: str,
        concept_direction: str = "",
        concept_image_bytes: bytes | None = None,
        concept_mime_type: str = "image/png",
    ) -> WorldBlueprint:
        grid = GridSpec()
        chunks = [
            ChunkSpec(
                chunk_x=x,
                chunk_z=z,
                generated=True,
                biome=(profile.terrain[(x + z) % len(profile.terrain)] if profile.terrain else "meadow"),
                theme_hint=profile.world_type,
            )
            for z in range(5)
            for x in range(5)
        ]

        visual_anchor = self.visual_anchor_service.extract(
            profile=profile,
            concept_direction=concept_direction,
            concept_path=concept_path,
            image_bytes=concept_image_bytes,
            mime_type=concept_mime_type,
        )
        layout_plan = self.layout_service.compile(
            profile=profile,
            anchor=visual_anchor,
            grid=grid,
        )

        spawn = SpawnPoint(x=6, y=0, z=25, facing_degrees=90)

        landmark_elements = [
            element
            for element in layout_plan.elements
            if element.kind in {"structure", "landmark", "bridge"}
        ][:6]
        landmarks = [
            LandmarkSpec(
                landmark_id=f"LANDMARK_{index+1:02d}",
                name=element.name,
                position=element.position.model_copy(deep=True),
                kind=element.kind,
                required_for_concept_match=True,
            )
            for index, element in enumerate(landmark_elements)
        ]

        portal_element = layout_plan.first("portal")
        portal_position = (
            portal_element.position.model_copy(deep=True)
            if portal_element is not None
            else WorldPoint(x=44, y=0, z=25)
        )
        portal = PortalSpec(
            position=portal_position,
            facing_degrees=270,
            form=profile.portal_form or (
                portal_element.name if portal_element is not None else "Portal"
            ),
            destination_hint="Next Mini World",
        )

        route_points = [WorldPoint(x=spawn.x, y=0, z=spawn.z)]
        route_points.extend(lm.position for lm in landmarks)
        route_points.append(portal_position)

        main_path = PathSpec(
            path_id="PATH_MAIN",
            name="Discovery Path",
            points=route_points,
            width_cells=2.5,
            walkable=True,
        )

        zones = [
            ZoneSpec(
                zone_id="ZONE_SPAWN",
                name="Arrival Area",
                kind="spawn",
                min_x=2,
                max_x=10,
                min_z=20,
                max_z=30,
            ),
            ZoneSpec(
                zone_id="ZONE_CORE",
                name="Core Exploration Area",
                kind="walkable",
                min_x=10,
                max_x=42,
                min_z=6,
                max_z=44,
            ),
            ZoneSpec(
                zone_id="ZONE_PORTAL",
                name="Portal Area",
                kind="portal",
                min_x=max(0, portal_position.x - 4),
                max_x=min(grid.width, portal_position.x + 4),
                min_z=max(0, portal_position.z - 4),
                max_z=min(grid.depth, portal_position.z + 4),
            ),
        ]
        water_zone_ids: list[str] = []
        for index, element in enumerate(
            item for item in layout_plan.elements if item.kind == "water"
        ):
            zone_id = f"ZONE_WATER_{index+1:02d}"
            water_zone_ids.append(zone_id)
            zones.append(
                ZoneSpec(
                    zone_id=zone_id,
                    name=element.name,
                    kind="water",
                    min_x=max(0, element.position.x - element.width / 2),
                    max_x=min(grid.width, element.position.x + element.width / 2),
                    min_z=max(0, element.position.z - element.depth / 2),
                    max_z=min(grid.depth, element.position.z + element.depth / 2),
                )
            )

        camera_points = [
            CameraPoint(
                camera_id="CAM_ESTABLISHING",
                position=WorldPoint(x=4, y=11, z=10),
                look_at=WorldPoint(x=24, y=2, z=25),
                lens_mm=28,
                role="establishing",
            ),
            CameraPoint(
                camera_id="CAM_FOLLOW",
                position=WorldPoint(x=10, y=4, z=25),
                look_at=WorldPoint(x=18, y=2, z=25),
                lens_mm=35,
                role="follow",
            ),
        ]
        for index, landmark in enumerate(landmarks[:2]):
            camera_points.append(
                CameraPoint(
                    camera_id=f"CAM_LANDMARK_{index+1:02d}",
                    position=WorldPoint(
                        x=max(0, landmark.position.x - 7),
                        y=6,
                        z=max(0, landmark.position.z - 7),
                    ),
                    look_at=landmark.position,
                    lens_mm=35,
                    role="landmark",
                )
            )
        camera_points.extend(
            [
                CameraPoint(
                    camera_id="CAM_PORTAL",
                    position=WorldPoint(
                        x=max(2, portal_position.x - 6),
                        y=5,
                        z=portal_position.z,
                    ),
                    look_at=portal_position,
                    lens_mm=40,
                    role="portal_reveal",
                ),
                CameraPoint(
                    camera_id="CAM_ENDING",
                    position=WorldPoint(x=48, y=12, z=42),
                    look_at=WorldPoint(x=28, y=1, z=25),
                    lens_mm=32,
                    role="ending",
                ),
            ]
        )

        director_tour = TourRoute(
            name="First World Tour",
            steps=[
                TourStep(camera_id=point.camera_id, duration_seconds=4.0, movement=(
                    "fly" if point.role == "establishing"
                    else "follow" if point.role == "follow"
                    else "orbit" if point.role == "landmark"
                    else "dolly" if point.role == "portal_reveal"
                    else "cut"
                ))
                for point in camera_points
            ],
        )

        return WorldBlueprint(
            location_asset_id=location_asset_id,
            style_asset_id=style_asset_id,
            grid=grid,
            spawn=spawn,
            chunks=chunks,
            landmarks=landmarks,
            portal=portal,
            paths=[main_path],
            zones=zones,
            walkable_zone_ids=["ZONE_SPAWN", "ZONE_CORE", "ZONE_PORTAL"],
            blocked_zone_ids=water_zone_ids,
            visual_anchor=visual_anchor,
            layout_elements=layout_plan.elements,
            camera_points=camera_points,
            director_tours=[director_tour],
        )
