from __future__ import annotations

from pathlib import Path

from studio.core.enums import AssetType
from studio.models.play_session import PlaySessionRuntimeSpec
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.equipment_service import EquipmentService
from studio.services.world_gameplay_layer_service import (
    WorldGameplayLayerService,
)
from studio.services.world_creative_layout_service import (
    WorldCreativeLayoutService,
)
from studio.services.world_runtime_binding_service import (
    WorldRuntimeBindingService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GODOT_PLAY_SESSION_PATH = (
    PROJECT_ROOT
    / "godot"
    / "runtime_state"
    / "creator_play_session.json"
)


class CreatorPlaySessionService:
    """Build/export one canonical Creator state for playable runtimes."""

    def __init__(
        self,
        repository: StudioRepository,
        character_runtime: CharacterRuntimeService,
        *,
        equipment: EquipmentService | None = None,
        babies: BabyService | None = None,
        export_path: str | Path | None = None,
    ):
        self.repository = repository
        self.character_runtime = character_runtime
        self.equipment = equipment or EquipmentService(repository)
        self.babies = babies or BabyService(repository)
        self.export_path = Path(export_path) if export_path else DEFAULT_GODOT_PLAY_SESSION_PATH

    def build(
        self,
        *,
        character_asset_id: str,
        world_asset_id: str | None = None,
        quest_id: str | None = None,
    ) -> PlaySessionRuntimeSpec:
        character_asset = self.repository.get_asset(character_asset_id)
        if (
            character_asset is None
            or character_asset.asset_type != AssetType.CHARACTER
        ):
            raise ValueError(f"Character not found: {character_asset_id}")

        quest = None
        if quest_id is not None:
            quest = self.repository.get_quest(quest_id)
            if quest is None:
                raise ValueError(f"Quest not found: {quest_id}")
            if world_asset_id is None:
                world_asset_id = quest.world_asset_id
            elif world_asset_id != quest.world_asset_id:
                raise ValueError(
                    "Quest World does not match requested PlaySession World."
                )

        world_name: str | None = None
        world_gameplay = None
        creative_layout = None
        world_runtime = None
        if world_asset_id is not None:
            world_asset = self.repository.get_asset(world_asset_id)
            if world_asset is None or world_asset.asset_type != AssetType.LOCATION:
                raise ValueError(f"World not found: {world_asset_id}")
            world_name = world_asset.display_name
            world_gameplay = WorldGameplayLayerService(
                self.repository
            ).get_layer(world_asset_id)
            creative_layout = WorldCreativeLayoutService(
                self.repository
            ).get_layout(world_asset_id)
            world_runtime = WorldRuntimeBindingService(
                self.repository
            ).binding_for(world_asset_id)

        return PlaySessionRuntimeSpec(
            character_asset_id=character_asset.asset_id,
            character_name=character_asset.display_name,
            character=self.character_runtime.resolve(character_asset),
            equipment=self.equipment.runtime_spec(character_asset.asset_id),
            baby=self.babies.runtime_spec(),
            quest=quest,
            world_gameplay=world_gameplay,
            creative_layout=creative_layout,
            world_runtime=world_runtime,
            world_asset_id=world_asset_id,
            world_name=world_name,
        )

    def export(
        self,
        *,
        character_asset_id: str,
        world_asset_id: str | None = None,
        quest_id: str | None = None,
    ) -> PlaySessionRuntimeSpec:
        spec = self.build(
            character_asset_id=character_asset_id,
            world_asset_id=world_asset_id,
            quest_id=quest_id,
        )
        spec.save_json(self.export_path)
        return spec
