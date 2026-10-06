from __future__ import annotations

import hashlib
import random
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from studio.core.ids import new_id
from studio.models.asset import now_utc


class EquipmentSlot(str, Enum):
    OUTFIT = "outfit"
    WEAPON_MAIN = "weapon_main"
    BACKPACK = "backpack"
    WINGS = "wings"
    ACCESSORY = "accessory"


class EquipmentRarity(str, Enum):
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    GOLD = "gold"
    RED = "red"
    RAINBOW = "rainbow"


RARITY_POWER_MULTIPLIER: dict[EquipmentRarity, float] = {
    EquipmentRarity.GREEN: 1.00,
    EquipmentRarity.BLUE: 1.25,
    EquipmentRarity.PURPLE: 1.55,
    EquipmentRarity.GOLD: 1.90,
    EquipmentRarity.RED: 2.35,
    EquipmentRarity.RAINBOW: 2.90,
}


class StatBlock(BaseModel):
    hp: int = Field(default=0, ge=0)
    atk: int = Field(default=0, ge=0)
    defense: int = Field(default=0, ge=0)

    @property
    def power(self) -> int:
        return self.hp + self.atk + self.defense

    def plus(self, other: "StatBlock") -> "StatBlock":
        return StatBlock(
            hp=self.hp + other.hp,
            atk=self.atk + other.atk,
            defense=self.defense + other.defense,
        )


class EquipmentDefinition(BaseModel):
    definition_id: str
    display_name: str
    slot: EquipmentSlot
    description: str = ""
    mesh_asset_id: str | None = None
    animation_class: str | None = None
    compatible_tags: list[str] = Field(default_factory=lambda: ["humanoid"])
    base_stats: StatBlock = Field(default_factory=StatBlock)


class EquipmentInstance(BaseModel):
    item_instance_id: str
    definition_id: str
    rarity: EquipmentRarity
    item_level: int = Field(default=1, ge=1, le=999)
    generation_seed: str
    rolled_stats: StatBlock
    affixes: list[str] = Field(default_factory=list)
    special_effect_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class CharacterLoadout(BaseModel):
    character_asset_id: str
    outfit_item_id: str | None = None
    weapon_main_item_id: str | None = None
    backpack_item_id: str | None = None
    wings_item_id: str | None = None
    accessory_item_id: str | None = None

    def item_id_for_slot(self, slot: EquipmentSlot) -> str | None:
        return getattr(self, f"{slot.value}_item_id")

    def with_item(self, slot: EquipmentSlot, item_id: str | None) -> "CharacterLoadout":
        return self.model_copy(update={f"{slot.value}_item_id": item_id})


class CreatorCollection(BaseModel):
    collection_id: str = "COLL_DEFAULT"
    owner_key: str = "default_creator"
    items: list[EquipmentInstance] = Field(default_factory=list)
    loadouts: dict[str, CharacterLoadout] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def unique_item_instances(self) -> "CreatorCollection":
        ids = [item.item_instance_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate equipment item_instance_id in collection.")
        return self

    def item_by_id(self, item_instance_id: str) -> EquipmentInstance | None:
        return next(
            (item for item in self.items if item.item_instance_id == item_instance_id),
            None,
        )

    def loadout_for(self, character_asset_id: str) -> CharacterLoadout:
        return self.loadouts.get(
            character_asset_id,
            CharacterLoadout(character_asset_id=character_asset_id),
        )


def deterministic_roll(
    *,
    definition: EquipmentDefinition,
    rarity: EquipmentRarity,
    item_level: int,
    generation_seed: str,
) -> StatBlock:
    """Roll bounded HP / ATK / DEF using a reproducible rarity power budget."""

    base = definition.base_stats
    base_power = max(1, base.power)
    multiplier = RARITY_POWER_MULTIPLIER[rarity]
    target_power = max(
        base_power,
        round((base_power + max(0, item_level - 1) * 2) * multiplier),
    )
    bonus_points = max(0, target_power - base_power)

    digest = hashlib.sha256(
        f"{definition.definition_id}|{rarity.value}|{item_level}|{generation_seed}".encode()
    ).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))

    values = {"hp": base.hp, "atk": base.atk, "defense": base.defense}
    weights = {
        "hp": max(1, base.hp),
        "atk": max(1, base.atk),
        "defense": max(1, base.defense),
    }
    weighted_keys = [
        key
        for key, weight in weights.items()
        for _ in range(weight)
    ]

    for _ in range(bonus_points):
        key = rng.choice(weighted_keys)
        values[key] += 1

    return StatBlock(**values)


def create_equipment_instance(
    *,
    definition: EquipmentDefinition,
    rarity: EquipmentRarity,
    item_level: int = 1,
    generation_seed: str | None = None,
) -> EquipmentInstance:
    seed = generation_seed or new_id("SEED")
    return EquipmentInstance(
        item_instance_id=new_id("ITEM"),
        definition_id=definition.definition_id,
        rarity=rarity,
        item_level=item_level,
        generation_seed=seed,
        rolled_stats=deterministic_roll(
            definition=definition,
            rarity=rarity,
            item_level=item_level,
            generation_seed=seed,
        ),
    )
