from __future__ import annotations

from studio.core.enums import AssetType
from studio.models.asset import now_utc
from studio.models.world_creative import (
    CREATIVE_PROP_LABELS,
    CreativePropType,
    WorldCreativeLayout,
    WorldDecoration,
)
from studio.models.world_gameplay import WorldExperienceMode
from studio.repositories.base import StudioRepository
from studio.services.world_gameplay_layer_service import WorldGameplayLayerService


WORLD_CREATIVE_METADATA_KEY = "world_creative_layout"


class WorldCreativeLayoutService:
    """Persist child-owned additive decoration deltas on one canonical World."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def _world(self, world_asset_id: str):
        world = self.repository.get_asset(world_asset_id)
        if world is None:
            raise ValueError(f"World not found: {world_asset_id}")
        if world.asset_type != AssetType.LOCATION:
            raise ValueError("Creative layout requires a Location asset.")
        return world

    def get_layout(self, world_asset_id: str) -> WorldCreativeLayout:
        world = self._world(world_asset_id)
        raw = world.metadata.get(WORLD_CREATIVE_METADATA_KEY)
        if not raw:
            return WorldCreativeLayout(world_asset_id=world_asset_id)
        layout = WorldCreativeLayout.model_validate(raw)
        if layout.world_asset_id != world_asset_id:
            raise ValueError("Creative layout references the wrong World.")
        return layout

    def save_layout(self, layout: WorldCreativeLayout) -> WorldCreativeLayout:
        world = self._world(layout.world_asset_id)
        layout.updated_at = now_utc()
        world.metadata[WORLD_CREATIVE_METADATA_KEY] = layout.model_dump(mode="json")
        world.metadata["world_creative_schema_version"] = layout.schema_version
        world.updated_at = layout.updated_at
        self.repository.save_asset(world)

        gameplay = WorldGameplayLayerService(self.repository).ensure_layer(
            layout.world_asset_id
        )
        if WorldExperienceMode.CREATIVE not in gameplay.modes:
            gameplay.modes.append(WorldExperienceMode.CREATIVE)
            WorldGameplayLayerService(self.repository).save_layer(gameplay)
        return layout

    def place(
        self,
        *,
        world_asset_id: str,
        prop_type: CreativePropType,
        position: tuple[float, float, float],
        rotation_y: float = 0.0,
        scale: float = 1.0,
    ) -> WorldDecoration:
        layout = self.get_layout(world_asset_id)
        item = WorldDecoration(
            prop_type=prop_type,
            display_name=CREATIVE_PROP_LABELS[prop_type],
            position=position,
            rotation_y=rotation_y,
            scale=scale,
        )
        layout.decorations.append(item)
        self.save_layout(layout)
        return item

    def remove(self, *, world_asset_id: str, decoration_id: str) -> bool:
        layout = self.get_layout(world_asset_id)
        before = len(layout.decorations)
        layout.decorations = [
            item
            for item in layout.decorations
            if item.decoration_id != decoration_id
        ]
        if len(layout.decorations) == before:
            return False
        self.save_layout(layout)
        return True

    def clear(self, world_asset_id: str) -> WorldCreativeLayout:
        layout = self.get_layout(world_asset_id)
        layout.decorations = []
        return self.save_layout(layout)
