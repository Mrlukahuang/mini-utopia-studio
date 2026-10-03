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
    WorldScenePlan,
    WorldVisualAnchor,
    ZoneSpec,
)
from studio.services.world_visual_anchor_service import WorldVisualAnchorService
from studio.services.world_layout_service import WorldLayoutPlan, WorldLayoutService


class WorldBlueprintService:
    """Build deterministic executable World Blueprints.

    The primary pipeline compiles a semantic Scene Plan. Legacy/image-to-world
    builds remain supported through the visual-anchor path.
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
        """Legacy deterministic profile planning kept for backward compatibility."""
        return self.build(
            location_asset_id=location_asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            concept_path="",
            concept_direction="blueprint_first",
            concept_image_bytes=None,
        )

    def plan_from_scene_plan(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
    ) -> WorldBlueprint:
        """Compile the shared Prompt/Custom Scene Plan into runtime truth."""
        grid, chunks = self._grid_and_chunks(profile)
        visual_anchor = WorldVisualAnchor(
            concept_image_roles=[],
            concept_path="",
            concept_direction=f"scene_plan:{scene_plan.source_mode}",
            extraction_method="scene_plan_v1",
            concept_summary=scene_plan.summary,
            must_preserve=[
                item.name for item in scene_plan.elements if item.required
            ],
            flexible_details=[
                item.name
                for item in scene_plan.elements
                if item.source == "utopia_enrichment"
            ],
            palette_hexes=list(profile.theme_color_hexes),
            composition_notes=[scene_plan.route_intent],
            spatial_relations=list(scene_plan.spatial_relations),
        )
        layout_plan = self.layout_service.compile_scene_plan(
            plan=scene_plan,
            grid=grid,
        )
        return self._assemble(
            location_asset_id=location_asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            grid=grid,
            chunks=chunks,
            visual_anchor=visual_anchor,
            layout_plan=layout_plan,
            scene_plan=scene_plan,
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
        """Legacy visual/profile compiler used by Image-to-World compatibility."""
        grid, chunks = self._grid_and_chunks(profile)
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
        return self._assemble(
            location_asset_id=location_asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            grid=grid,
            chunks=chunks,
            visual_anchor=visual_anchor,
            layout_plan=layout_plan,
            scene_plan=None,
        )

    @staticmethod
    def _grid_and_chunks(profile: WorldProfile) -> tuple[GridSpec, list[ChunkSpec]]:
        grid = GridSpec()
        chunks = [
            ChunkSpec(
                chunk_x=x,
                chunk_z=z,
                generated=True,
                biome=(
                    profile.terrain[(x + z) % len(profile.terrain)]
                    if profile.terrain
                    else "meadow"
                ),
                theme_hint=profile.world_type,
            )
            for z in range(5)
            for x in range(5)
        ]
        return grid, chunks

    def _assemble(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
        profile: WorldProfile,
        grid: GridSpec,
        chunks: list[ChunkSpec],
        visual_anchor: WorldVisualAnchor,
        layout_plan: WorldLayoutPlan,
        scene_plan: WorldScenePlan | None,
    ) -> WorldBlueprint:
        spawn = SpawnPoint(x=6, y=0, z=25, facing_degrees=90)

        landmark_elements = [
            element
            for element in layout_plan.elements
            if element.kind in {"structure", "landmark", "bridge"}
        ][:8]
        landmarks = [
            LandmarkSpec(
                landmark_id=f"LANDMARK_{index+1:02d}",
                name=element.name,
                position=element.position.model_copy(deep=True),
                kind=element.kind,
                geometry_role=element.geometry_role,
                orientation=element.orientation,
                spatial_mode=element.spatial_mode,
                traversability=element.traversability,
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
            form=(
                portal_element.name
                if portal_element is not None
                else profile.portal_form or "Portal"
            ),
            destination_hint="Next Mini World",
        )

        by_id = {element.element_id: element for element in layout_plan.elements}
        route_points = [WorldPoint(x=spawn.x, y=0, z=spawn.z)]
        if scene_plan is not None:
            for scene_id in scene_plan.exploration_order:
                element = by_id.get(scene_id)
                if element is None or element.kind == "portal":
                    continue
                if element.traversability in {"blocked", "decorative"}:
                    # Blocked features can still receive a scenic edge viewpoint
                    # when they are meaningful water/landmarks.
                    if element.kind in {"water", "landmark", "structure"}:
                        route_points.append(self._safe_route_point(element, grid))
                    continue
                route_points.append(self._safe_route_point(element, grid))
        else:
            route_points.extend(
                landmark.position.model_copy(deep=True)
                for landmark in landmarks
            )
        route_points.append(portal_position.model_copy(deep=True))
        route_points = self._dedupe_points(route_points)

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
            item
            for item in layout_plan.elements
            if item.kind == "water"
            and item.traversability == "blocked"
            and item.geometry_role == "surface"
            and item.spatial_mode in {"grounded", "elevated"}
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

        max_scene_y = max(
            (
                element.position.y + element.height
                for element in layout_plan.elements
            ),
            default=6.0,
        )
        establishing_y = max(11.0, min(28.0, max_scene_y + 5.0))
        follow_target = (
            route_points[1]
            if len(route_points) > 1
            else WorldPoint(x=18, y=2, z=25)
        )
        camera_points = [
            CameraPoint(
                camera_id="CAM_ESTABLISHING",
                position=WorldPoint(x=4, y=establishing_y, z=10),
                look_at=WorldPoint(x=24, y=max(2.0, max_scene_y * .4), z=25),
                lens_mm=28,
                role="establishing",
            ),
            CameraPoint(
                camera_id="CAM_FOLLOW",
                position=WorldPoint(
                    x=10,
                    y=max(4.0, follow_target.y + 4.0),
                    z=25,
                ),
                look_at=follow_target,
                lens_mm=35,
                role="follow",
            ),
        ]

        photo_elements = []
        if scene_plan is not None:
            for scene_id in scene_plan.photo_spot_ids:
                element = by_id.get(scene_id)
                if (
                    element is not None
                    and element.kind != "portal"
                    and element not in photo_elements
                ):
                    photo_elements.append(element)
                if len(photo_elements) >= 4:
                    break
        else:
            photo_elements = landmark_elements[:2]

        for index, element in enumerate(photo_elements):
            target = element.position.model_copy(deep=True)
            camera_points.append(
                CameraPoint(
                    camera_id=f"CAM_PHOTO_{index+1:02d}",
                    position=WorldPoint(
                        x=max(2, min(grid.width - 2, target.x - 7)),
                        y=max(6.0, target.y + element.height * .65 + 3.0),
                        z=max(2, min(grid.depth - 2, target.z - 7)),
                    ),
                    look_at=WorldPoint(
                        x=target.x,
                        y=target.y + element.height * .45,
                        z=target.z,
                    ),
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
                        y=max(5.0, portal_position.y + 5.0),
                        z=portal_position.z,
                    ),
                    look_at=WorldPoint(
                        x=portal_position.x,
                        y=portal_position.y + 3.0,
                        z=portal_position.z,
                    ),
                    lens_mm=40,
                    role="portal_reveal",
                ),
                CameraPoint(
                    camera_id="CAM_ENDING",
                    position=WorldPoint(
                        x=48,
                        y=max(12.0, min(28.0, max_scene_y + 3.0)),
                        z=42,
                    ),
                    look_at=WorldPoint(
                        x=28,
                        y=max(1.0, max_scene_y * .35),
                        z=25,
                    ),
                    lens_mm=32,
                    role="ending",
                ),
            ]
        )

        director_tour = TourRoute(
            name="First World Tour",
            steps=[
                TourStep(
                    camera_id=point.camera_id,
                    duration_seconds=4.0,
                    movement=(
                        "fly"
                        if point.role == "establishing"
                        else "follow"
                        if point.role == "follow"
                        else "orbit"
                        if point.role == "landmark"
                        else "dolly"
                        if point.role == "portal_reveal"
                        else "cut"
                    ),
                )
                for point in camera_points
            ],
            character_route_point_ids=(
                list(scene_plan.exploration_order)
                if scene_plan is not None
                else []
            ),
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

    @staticmethod
    def _safe_route_point(element, grid: GridSpec) -> WorldPoint:
        """Return a walkable/scenic approach point while preserving elevation."""
        if element.traversability == "blocked" or element.kind == "water":
            route_y = element.position.y
            if element.geometry_role == "vertical_flow":
                # Visit the receiving/base level of a vertical flow instead of
                # trying to walk through its volume.
                route_y = max(0.0, element.position.y)
            return WorldPoint(
                x=max(
                    5,
                    min(
                        grid.width - 5,
                        element.position.x - element.width / 2 - 2,
                    ),
                ),
                y=route_y,
                z=max(5, min(grid.depth - 5, element.position.z)),
            )
        return element.position.model_copy(deep=True)

    @staticmethod
    def _dedupe_points(points: list[WorldPoint]) -> list[WorldPoint]:
        result: list[WorldPoint] = []
        for point in points:
            if result and (
                abs(result[-1].x - point.x) < .01
                and abs(result[-1].z - point.z) < .01
            ):
                continue
            result.append(point)
        return result
