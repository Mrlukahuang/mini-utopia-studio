from __future__ import annotations

from pydantic import BaseModel, Field

from studio.core.enums import AssetType, ReviewStatus
from studio.models.equipment import PLAYABLE_EQUIPMENT_SLOTS
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService


FIRST_REWARD_SLUG = "reward_bone_buckler"


class FirstAdventureProgress(BaseModel):
    """Persisted-state view of the first child-visible gameplay loop."""

    character_asset_id: str | None = None
    character_name: str | None = None
    has_character: bool = False
    has_active_baby: bool = False
    equipped_slots: list[str] = Field(default_factory=list)
    gear_ready: bool = False
    reward_claimed: bool = False
    reward_equipped: bool = False

    @property
    def completed_steps(self) -> int:
        return sum(
            (
                self.has_character,
                self.has_active_baby,
                self.gear_ready,
                self.reward_claimed,
            )
        )

    @property
    def total_steps(self) -> int:
        return 4

    @property
    def progress_fraction(self) -> float:
        return self.completed_steps / self.total_steps

    @property
    def loop_complete(self) -> bool:
        # The first loop is proven only by a real claimed Skeleton reward.
        return self.reward_claimed

    @property
    def next_hint(self) -> str:
        if not self.has_character:
            return "先创造第一个 Character。"
        if not self.has_active_baby:
            return "去 My Baby 领取你的 Initial Baby。"
        if not self.gear_ready:
            return "去 Dressing Room 穿上第一套装备。"
        if not self.reward_claimed:
            return "带这套装备进入 Newbie Village，击败 Training Skeleton，再回 My Stuff 领取掉落。"
        if not self.reward_equipped:
            return "Bone Buckler 已经属于你了。去 Dressing Room 装上它，再出发一次！"
        return "第一条成长循环完成！现在你可以带着更强的装备再次出发。"


class FirstAdventureProgressService:
    """Derive first-loop progress only from durable Creator state."""

    def __init__(
        self,
        repository: StudioRepository,
        *,
        equipment: EquipmentService | None = None,
        babies: BabyService | None = None,
    ):
        self.repository = repository
        self.equipment = equipment or EquipmentService(repository)
        self.babies = babies or BabyService(repository)

    def status(self) -> FirstAdventureProgress:
        characters = [
            asset
            for asset in self.repository.list_assets(AssetType.CHARACTER)
            if asset.status != ReviewStatus.ARCHIVED
            and "character_profile" in asset.metadata
        ]
        if not characters:
            return FirstAdventureProgress()

        character = characters[0]
        collection = self.equipment.ensure_starter_collection()
        definitions = self.equipment.list_definitions()
        loadout = collection.loadout_for(character.asset_id)

        equipped_slots = [
            slot.value
            for slot in PLAYABLE_EQUIPMENT_SLOTS
            if loadout.item_id_for_slot(slot)
        ]

        reward_definition_ids = {
            asset.asset_id
            for asset in self.repository.list_assets(AssetType.EQUIPMENT)
            if asset.slug == FIRST_REWARD_SLUG
        }
        reward_items = [
            item
            for item in collection.items
            if item.definition_id in reward_definition_ids
        ]
        reward_item_ids = {item.item_instance_id for item in reward_items}
        reward_claimed = bool(reward_items)
        reward_equipped = any(
            loadout.item_id_for_slot(slot) in reward_item_ids
            for slot in PLAYABLE_EQUIPMENT_SLOTS
        )

        return FirstAdventureProgress(
            character_asset_id=character.asset_id,
            character_name=character.display_name,
            has_character=True,
            has_active_baby=self.babies.active_baby() is not None,
            equipped_slots=equipped_slots,
            gear_ready=bool(equipped_slots),
            reward_claimed=reward_claimed,
            reward_equipped=reward_equipped,
        )
