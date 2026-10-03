from __future__ import annotations

from studio.core.enums import AssetType
from studio.models.asset import now_utc
from studio.models.world import WorldBlueprint, WorldPoint
from studio.repositories.base import StudioRepository


MOVE_STEP = 4.0
SCALE_UP = 1.18
SCALE_DOWN = 0.85


class WorldConceptMatchService:
    """Apply human layout corrections to a saved playable World Blueprint."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def apply_correction(
        self,
        *,
        location_asset_id: str,
        element_id: str,
        action: str,
    ) -> WorldBlueprint:
        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        raw_blueprint = world.metadata.get("world_blueprint")
        if not raw_blueprint:
            raise ValueError("World does not have a playable Blueprint.")

        blueprint = WorldBlueprint.model_validate(raw_blueprint)
        element = next(
            (item for item in blueprint.layout_elements if item.element_id == element_id),
            None,
        )
        if element is None:
            raise ValueError(f"Layout element not found: {element_id}")

        before = {
            "x": element.position.x,
            "z": element.position.z,
            "width": element.width,
            "depth": element.depth,
        }

        if action == "left":
            element.position.x -= MOVE_STEP
        elif action == "right":
            element.position.x += MOVE_STEP
        elif action == "forward":
            element.position.z += MOVE_STEP
        elif action == "back":
            element.position.z -= MOVE_STEP
        elif action == "bigger":
            element.width *= SCALE_UP
            element.depth *= SCALE_UP
        elif action == "smaller":
            element.width *= SCALE_DOWN
            element.depth *= SCALE_DOWN
        else:
            raise ValueError(f"Unsupported concept-match action: {action}")

        element.position.x = self._clamp(
            element.position.x, 3.0, blueprint.grid.width - 3.0
        )
        element.position.z = self._clamp(
            element.position.z, 3.0, blueprint.grid.depth - 3.0
        )
        element.width = self._clamp(element.width, 2.0, blueprint.grid.width * .7)
        element.depth = self._clamp(element.depth, 2.0, blueprint.grid.depth * .7)
        element.source_evidence.append(f"human_review:{action}")

        self._sync_semantic_references(blueprint, element_id)
        self._rebuild_discovery_path(blueprint)
        self._sync_cameras(blueprint)

        world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
        history = list(world.metadata.get("world_concept_match_history", []))
        history.append(
            {
                "element_id": element.element_id,
                "name": element.name,
                "action": action,
                "before": before,
                "after": {
                    "x": element.position.x,
                    "z": element.position.z,
                    "width": element.width,
                    "depth": element.depth,
                },
                "timestamp": now_utc().isoformat(),
            }
        )
        world.metadata["world_concept_match_history"] = history[-100:]
        world.metadata["world_concept_match_reviewed"] = True
        world.updated_at = now_utc()
        self.repository.save_asset(world)

        persisted = self.repository.get_asset(location_asset_id)
        if persisted is None:
            raise RuntimeError("World disappeared after concept-match correction.")
        return WorldBlueprint.model_validate(persisted.metadata["world_blueprint"])

    def mark_reviewed(self, *, location_asset_id: str) -> None:
        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")
        if not world.metadata.get("world_blueprint"):
            raise ValueError("World does not have a playable Blueprint.")
        world.metadata["world_concept_match_reviewed"] = True
        world.metadata["world_concept_match_reviewed_at"] = now_utc().isoformat()
        world.updated_at = now_utc()
        self.repository.save_asset(world)

    @staticmethod
    def _sync_semantic_references(
        blueprint: WorldBlueprint,
        element_id: str,
    ) -> None:
        element = next(
            item for item in blueprint.layout_elements if item.element_id == element_id
        )

        if element.kind == "portal" and blueprint.portal is not None:
            blueprint.portal.position = element.position.model_copy(deep=True)

        if element.kind in {"structure", "landmark", "bridge"}:
            landmark = next(
                (item for item in blueprint.landmarks if item.name == element.name),
                None,
            )
            if landmark is not None:
                landmark.position = element.position.model_copy(deep=True)

        if element.kind == "water":
            zone = next(
                (
                    item
                    for item in blueprint.zones
                    if item.kind == "water" and item.name == element.name
                ),
                None,
            )
            if zone is not None:
                zone.min_x = max(0, element.position.x - element.width / 2)
                zone.max_x = min(
                    blueprint.grid.width, element.position.x + element.width / 2
                )
                zone.min_z = max(0, element.position.z - element.depth / 2)
                zone.max_z = min(
                    blueprint.grid.depth, element.position.z + element.depth / 2
                )

        portal_zone = next(
            (item for item in blueprint.zones if item.kind == "portal"),
            None,
        )
        if element.kind == "portal" and portal_zone is not None:
            portal_zone.min_x = max(0, element.position.x - 4)
            portal_zone.max_x = min(blueprint.grid.width, element.position.x + 4)
            portal_zone.min_z = max(0, element.position.z - 4)
            portal_zone.max_z = min(blueprint.grid.depth, element.position.z + 4)

    @staticmethod
    def _rebuild_discovery_path(blueprint: WorldBlueprint) -> None:
        if not blueprint.paths:
            return
        route = [
            WorldPoint(
                x=blueprint.spawn.x,
                y=blueprint.spawn.y,
                z=blueprint.spawn.z,
            )
        ]
        route.extend(
            landmark.position.model_copy(deep=True)
            for landmark in blueprint.landmarks
        )
        if blueprint.portal is not None:
            route.append(blueprint.portal.position.model_copy(deep=True))
        blueprint.paths[0].points = route

    @staticmethod
    def _sync_cameras(blueprint: WorldBlueprint) -> None:
        portal = blueprint.portal
        if portal is not None:
            portal_cam = next(
                (item for item in blueprint.camera_points if item.role == "portal_reveal"),
                None,
            )
            if portal_cam is not None:
                portal_cam.position = WorldPoint(
                    x=max(2, portal.position.x - 6),
                    y=5,
                    z=portal.position.z,
                )
                portal_cam.look_at = portal.position.model_copy(deep=True)

        landmark_cams = [
            item for item in blueprint.camera_points if item.role == "landmark"
        ]
        for camera, landmark in zip(landmark_cams, blueprint.landmarks[: len(landmark_cams)]):
            camera.position = WorldPoint(
                x=max(2, landmark.position.x - 7),
                y=6,
                z=max(2, landmark.position.z - 7),
            )
            camera.look_at = landmark.position.model_copy(deep=True)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
