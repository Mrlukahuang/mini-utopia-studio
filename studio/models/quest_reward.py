from __future__ import annotations

from pydantic import BaseModel, Field

from studio.models.equipment import EquipmentRarity, EquipmentSlot


class QuestCompletionReceipt(BaseModel):
    completion_id: str = Field(min_length=1)
    quest_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    character_asset_id: str = ""
    created_at: str = ""


class QuestRewardInbox(BaseModel):
    schema_version: str = "1.0"
    completions: list[QuestCompletionReceipt] = Field(default_factory=list)


class QuestRewardClaim(BaseModel):
    claim_id: str
    completion_id: str
    quest_id: str
    reward_id: str
    item_instance_id: str
    display_name: str
    rarity: EquipmentRarity
    slot: EquipmentSlot
