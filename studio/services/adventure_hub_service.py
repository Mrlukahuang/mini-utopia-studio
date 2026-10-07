from __future__ import annotations

from pydantic import BaseModel, Field

from studio.core.enums import AssetType
from studio.models.equipment import EquipmentRarity
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.world_creative_layout_service import WorldCreativeLayoutService
from studio.services.world_gameplay_layer_service import WorldGameplayLayerService


class HubQuestState(BaseModel):
    quest_id: str
    title: str
    world_asset_id: str
    world_name: str


class HubBabyState(BaseModel):
    display_name: str
    level: int
    xp: int
    bond: int


class HubRewardState(BaseModel):
    item_instance_id: str
    display_name: str
    rarity: EquipmentRarity


class HubWorldState(BaseModel):
    world_asset_id: str
    world_name: str
    modes: list[str] = Field(default_factory=list)
    quest_count: int = 0
    story_count: int = 0
    decoration_count: int = 0


class AdventureHubState(BaseModel):
    quest: HubQuestState | None = None
    baby: HubBabyState | None = None
    latest_reward: HubRewardState | None = None
    world: HubWorldState | None = None

    @property
    def continue_page(self) -> str:
        if self.quest is not None:
            return "🪞 Dressing Room"
        if self.world is not None:
            return "🎮 Explore World"
        return "🌍 World Factory"


class AdventureHubService:
    """Derive the child-facing Home hub from durable repository state."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def _current_quest(self):
        quests = self.repository.list_quests()
        if not quests:
            return None
        return max(quests, key=lambda quest: quest.updated_at)

    def _current_world(self, quest):
        if quest is not None:
            return self.repository.get_asset(quest.world_asset_id)
        worlds = self.repository.list_assets(AssetType.LOCATION)
        if not worlds:
            return None
        return max(worlds, key=lambda world: world.updated_at)

    def status(self) -> AdventureHubState:
        quest = self._current_quest()
        world = self._current_world(quest)

        quest_state = None
        if quest is not None and world is not None:
            quest_state = HubQuestState(
                quest_id=quest.quest_id,
                title=quest.title,
                world_asset_id=world.asset_id,
                world_name=world.display_name,
            )

        baby = BabyService(self.repository).active_baby()
        baby_state = (
            HubBabyState(
                display_name=baby.display_name,
                level=baby.level,
                xp=baby.xp,
                bond=baby.bond,
            )
            if baby is not None
            else None
        )

        equipment = EquipmentService(self.repository)
        collection = equipment.ensure_starter_collection()
        definitions = equipment.list_definitions()
        latest_reward = None
        if collection.items:
            newest = max(collection.items, key=lambda item: item.created_at)
            definition = definitions.get(newest.definition_id)
            if definition is not None:
                latest_reward = HubRewardState(
                    item_instance_id=newest.item_instance_id,
                    display_name=definition.display_name,
                    rarity=newest.rarity,
                )

        world_state = None
        if world is not None:
            gameplay = WorldGameplayLayerService(self.repository).get_layer(
                world.asset_id
            )
            creative = WorldCreativeLayoutService(self.repository).get_layout(
                world.asset_id
            )
            world_state = HubWorldState(
                world_asset_id=world.asset_id,
                world_name=world.display_name,
                modes=(
                    [mode.value for mode in gameplay.modes]
                    if gameplay is not None
                    else ["explore"]
                ),
                quest_count=(
                    len(gameplay.quest_ids)
                    if gameplay is not None
                    else 0
                ),
                story_count=(
                    len(gameplay.story_ids)
                    if gameplay is not None
                    else 0
                ),
                decoration_count=len(creative.decorations),
            )

        return AdventureHubState(
            quest=quest_state,
            baby=baby_state,
            latest_reward=latest_reward,
            world=world_state,
        )
