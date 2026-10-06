from __future__ import annotations

from pydantic import BaseModel, Field

from studio.models.equipment import EquipmentRarity, EquipmentSlot


COMBAT_DROP_SCHEMA_VERSION = "1.0"


class CombatDropReceipt(BaseModel):
    drop_id: str
    source_enemy: str
    definition_slug: str
    rarity: EquipmentRarity
    item_level: int = Field(default=1, ge=1, le=999)
    generation_seed: str
    character_asset_id: str | None = None
    created_at: str = ""


class CombatDropInbox(BaseModel):
    schema_version: str = COMBAT_DROP_SCHEMA_VERSION
    drops: list[CombatDropReceipt] = Field(default_factory=list)


class CombatDropClaim(BaseModel):
    drop_id: str
    item_instance_id: str
    display_name: str
    rarity: EquipmentRarity
    slot: EquipmentSlot
