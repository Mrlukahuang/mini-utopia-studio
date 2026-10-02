from __future__ import annotations

from studio.models.world import (
    CameraPoint,
    ChunkSpec,
    LandmarkSpec,
    PathSpec,
    PortalSpec,
    SpawnPoint,
    TourRoute,
    TourStep,
    WorldBlueprint,
    WorldPoint,
    WorldProfile,
    WorldVisualAnchor,
    ZoneSpec,
)


class WorldBlueprintService:
    """Build a deterministic structural Blueprint from an approved World concept.

    M3 deliberately creates stable data first. Later versions may use vision/LLM
    analysis to refine the same schema without changing the runtime contract.
    """

    def build(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
        profile: WorldProfile,
        concept_path: str,
        concept_direction: str = "",
    ) -> WorldBlueprint:
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

        spawn = SpawnPoint(x=6, y=0, z=25, facing_degrees=90)

        landmark_positions = [
            WorldPoint(x=25, y=0, z=25),
            WorldPoint(x=36, y=0, z=15),
            WorldPoint(x=35, y=0, z=36),
            WorldPoint(x=18, y=0, z=38),
        ]
        landmarks = [
            LandmarkSpec(
                landmark_id=f"LANDMARK_{index+1:02d}",
                name=name,
                position=landmark_positions[index],
                kind=name,
                required_for_concept_match=True,
            )
            for index, name in enumerate(profile.landmark_ideas[:4])
        ]

        portal_position = WorldPoint(x=44, y=0, z=25)
        portal = PortalSpec(
            position=portal_position,
            facing_degrees=270,
            form=profile.portal_form,
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
                min_x=41,
                max_x=48,
                min_z=21,
                max_z=29,
            ),
        ]

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
                    position=WorldPoint(x=38, y=5, z=25),
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
            spawn=spawn,
            chunks=chunks,
            landmarks=landmarks,
            portal=portal,
            paths=[main_path],
            zones=zones,
            walkable_zone_ids=["ZONE_SPAWN", "ZONE_CORE", "ZONE_PORTAL"],
            blocked_zone_ids=[],
            visual_anchor=WorldVisualAnchor(
                concept_image_roles=["world_concept_approved"],
                concept_summary=(
                    f"{profile.world_name} · {concept_direction or 'approved concept'} · "
                    f"{profile.source_description}"
                ).strip(" ·"),
                must_preserve=list(profile.landmark_ideas),
                flexible_details=list(profile.surprise_elements),
            ),
            camera_points=camera_points,
            director_tours=[director_tour],
        )
