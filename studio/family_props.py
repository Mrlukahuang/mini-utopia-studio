"""Private, child-authored procedural wearable props (no file uploads).

A crafted prop is a canonical Equipment asset + owner-scoped EquipmentInstance.
Its visual recipe is structured, bounded geometry that both Godot game and
Director can render without granting clients arbitrary 3D code or mesh URLs.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio.core.enums import AssetType, ReviewStatus
from studio.core.ids import new_id
from studio.models.asset import Asset, now_utc
from studio.models.equipment import (
    EquipmentDefinition, EquipmentInstance, EquipmentRarity,
    EquipmentSlot, StatBlock,
)
from studio.repositories.base import StudioRepository
from studio.services.equipment_service import EquipmentService
from studio.services.asset_service import slugify


MAX_CRAFTED_PROPS_PER_CHILD = 24


class FamilyCraftedProp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    display_name: str = Field(min_length=1, max_length=32, pattern=r"^[^<>\\/\x00-\x1f]+$")
    slot: Literal["headwear", "accessory", "weapon_main", "backpack"] = "accessory"
    shape: Literal["star", "sphere", "box", "heart"] = "star"
    color_hex: str = Field(default="#F7B7D2", pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color_hex: str = Field(default="#F2C75C", pattern=r"^#[0-9a-fA-F]{6}$")


def craft_family_prop(
    repository: StudioRepository,
    *,
    owner: str,
    character_id: str,
    request: FamilyCraftedProp,
) -> dict:
    """Create once in the canonical database; never invent an in-game copy."""
    service = EquipmentService(
        repository, collection_id="COLL_FAMILY_" + owner, owner_key=owner,
    )
    collection = service.ensure_starter_collection()
    owned_crafted = sum(
        1
        for item in collection.items
        if item.definition_id.startswith("EQ_")
        and (
            (asset := repository.get_asset(item.definition_id)) is not None
            and asset.metadata.get("family_owner") == owner
            and asset.metadata.get("family_crafted_prop") is True
        )
    )
    if owned_crafted >= MAX_CRAFTED_PROPS_PER_CHILD:
        raise ValueError("Crafted prop limit reached")

    name = request.display_name.strip()
    if not name:
        raise ValueError("A prop must have a name")
    slot = EquipmentSlot(request.slot)
    recipe = {
        "schema_version": "1.0",
        "shape": request.shape,
        "color_hex": request.color_hex.upper(),
        "accent_color_hex": request.accent_color_hex.upper(),
    }
    asset = Asset.create(
        AssetType.EQUIPMENT,
        display_name=name,
        slug=slugify(name) + "-" + new_id("CRAFT").lower(),
        status=ReviewStatus.APPROVED,
        metadata={
            "family_owner": owner,
            "family_crafted_prop": True,
            "visual_recipe": recipe,
        },
    )
    definition = EquipmentDefinition(
        definition_id=asset.asset_id,
        display_name=name,
        slot=slot,
        description="Created in the private Mini Utopia family wardrobe.",
        base_stats=StatBlock(),
        compatible_tags=["humanoid"],
    )
    asset.metadata["equipment_definition"] = definition.model_dump(mode="json")
    asset.metadata["equipment_schema_version"] = 2

    # Persist as two canonical entities, not an editable JSON "view".
    # Instances are scoped to the child's private collection.
    instance = EquipmentInstance(
        item_instance_id=new_id("ITEM"),
        definition_id=asset.asset_id,
        rarity=EquipmentRarity.GREEN,
        item_level=1,
        generation_seed=new_id("SEED"),
        rolled_stats=StatBlock(),  # Decoration cannot mint power/stat boosts.
    )
    repository.save_asset(asset)
    collection.items.append(instance)
    collection.updated_at = now_utc()
    repository.save_collection(collection)
    return {
        "schema_version": "1.0",
        "character_id": character_id,
        "prop_asset_id": asset.asset_id,
        "item_instance_id": instance.item_instance_id,
        "visual_recipe": recipe,
    }
