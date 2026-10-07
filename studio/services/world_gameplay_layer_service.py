from __future__ import annotations

from studio.core.enums import AssetType
from studio.models.asset import now_utc
from studio.models.world_gameplay import (
    WorldExperienceMode,
    WorldGameplayLayer,
    WorldGameplayTarget,
)
from studio.repositories.base import StudioRepository


WORLD_GAMEPLAY_METADATA_KEY = "world_gameplay_layer"


class WorldGameplayLayerService:
    """Add reusable gameplay references on top of one canonical World Asset."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def _world(self, world_asset_id: str):
        world = self.repository.get_asset(world_asset_id)
        if world is None:
            raise ValueError(f"World not found: {world_asset_id}")
        if world.asset_type != AssetType.LOCATION:
            raise ValueError("World gameplay layer requires a Location asset.")
        return world

    def get_layer(self, world_asset_id: str) -> WorldGameplayLayer | None:
        world = self._world(world_asset_id)
        raw = world.metadata.get(WORLD_GAMEPLAY_METADATA_KEY)
        if not raw:
            return None
        layer = WorldGameplayLayer.model_validate(raw)
        if layer.world_asset_id != world_asset_id:
            raise ValueError("World gameplay layer references the wrong World.")
        return layer

    def save_layer(self, layer: WorldGameplayLayer) -> WorldGameplayLayer:
        world = self._world(layer.world_asset_id)
        layer.updated_at = now_utc()
        world.metadata[WORLD_GAMEPLAY_METADATA_KEY] = layer.model_dump(
            mode="json"
        )
        world.metadata["world_gameplay_schema_version"] = (
            layer.schema_version
        )
        world.updated_at = layer.updated_at
        self.repository.save_asset(world)
        return layer

    def ensure_layer(self, world_asset_id: str) -> WorldGameplayLayer:
        existing = self.get_layer(world_asset_id)
        if existing is not None:
            return existing
        return self.save_layer(
            WorldGameplayLayer(world_asset_id=world_asset_id)
        )

    @staticmethod
    def _target_from_objective(objective) -> WorldGameplayTarget | None:
        if not objective.target_id:
            return None
        raw_position = objective.metadata.get("position")
        position = None
        if (
            isinstance(raw_position, (list, tuple))
            and len(raw_position) >= 3
        ):
            position = (
                float(raw_position[0]),
                float(raw_position[1]),
                float(raw_position[2]),
            )
        return WorldGameplayTarget(
            target_id=objective.target_id,
            target_type=objective.objective_type.value,
            position=position,
            metadata={
                key: value
                for key, value in objective.metadata.items()
                if key != "position"
            },
        )

    def register_quest(self, quest_id: str) -> WorldGameplayLayer:
        quest = self.repository.get_quest(quest_id)
        if quest is None:
            raise ValueError(f"Quest not found: {quest_id}")

        layer = self.ensure_layer(quest.world_asset_id)
        if WorldExperienceMode.QUEST not in layer.modes:
            layer.modes.append(WorldExperienceMode.QUEST)
        if quest.quest_id not in layer.quest_ids:
            layer.quest_ids.append(quest.quest_id)

        if quest.story_id:
            if WorldExperienceMode.STORY_PLAY not in layer.modes:
                layer.modes.append(WorldExperienceMode.STORY_PLAY)
            if quest.story_id not in layer.story_ids:
                layer.story_ids.append(quest.story_id)

        existing_targets = {
            target.target_id: target
            for target in layer.targets
        }
        for objective in quest.objectives:
            target = self._target_from_objective(objective)
            if target is not None:
                existing_targets[target.target_id] = target
        layer.targets = list(existing_targets.values())
        return self.save_layer(layer)
