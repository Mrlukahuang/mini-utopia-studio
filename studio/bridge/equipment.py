from __future__ import annotations

from studio.core.enums import AssetType
from studio.models.equipment import EquipmentSlot, PLAYABLE_EQUIPMENT_SLOTS
from studio.repositories.base import StudioRepository
from studio.services.equipment_service import EquipmentService


BRIDGE_EQUIPMENT_SCHEMA_VERSION = "2.0"


class EquipmentBridgeGateway:
    """Thin Bridge adapter over the canonical EquipmentService.

    The Bridge owns no inventory/loadout state. Every read and write goes
    through EquipmentService and the configured StudioRepository.
    """

    def __init__(self, repository: StudioRepository):
        self.repository = repository
        self.service = EquipmentService(repository)

    def get_state(self, character_id: str) -> dict | None:
        asset = self.repository.get_asset(character_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            return None

        collection = self.service.ensure_starter_collection()
        definitions = self.service.list_definitions()
        loadout = collection.loadout_for(character_id)
        runtime = self.service.runtime_spec(character_id)

        equipped_ids = {
            item_id
            for slot in PLAYABLE_EQUIPMENT_SLOTS
            if (item_id := loadout.item_id_for_slot(slot))
        }

        items: list[dict] = []
        for item in collection.items:
            definition = definitions.get(item.definition_id)
            if definition is None:
                continue
            if definition.slot not in PLAYABLE_EQUIPMENT_SLOTS:
                continue
            items.append(
                {
                    "item_instance_id": item.item_instance_id,
                    "definition_id": definition.definition_id,
                    "display_name": definition.display_name,
                    "description": definition.description,
                    "slot": definition.slot.value,
                    "rarity": item.rarity.value,
                    "item_level": item.item_level,
                    "rolled_stats": item.rolled_stats.model_dump(mode="json"),
                    "mesh_asset_id": definition.mesh_asset_id,
                    "animation_class": definition.animation_class,
                    "equipped": item.item_instance_id in equipped_ids,
                }
            )

        slot_order = {
            slot.value: index
            for index, slot in enumerate(PLAYABLE_EQUIPMENT_SLOTS)
        }
        items.sort(
            key=lambda item: (
                slot_order.get(item["slot"], 999),
                item["display_name"],
                item["item_instance_id"],
            )
        )

        return {
            "schema_version": BRIDGE_EQUIPMENT_SCHEMA_VERSION,
            "character_id": character_id,
            "slots": [slot.value for slot in PLAYABLE_EQUIPMENT_SLOTS],
            "loadout": loadout.model_dump(mode="json"),
            "items": items,
            "final_stats": runtime.final_stats.model_dump(mode="json"),
            "runtime": runtime.model_dump(mode="json"),
        }

    def set_slot(
        self,
        character_id: str,
        slot_value: str,
        item_instance_id: str | None,
    ) -> dict | None:
        asset = self.repository.get_asset(character_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            return None

        try:
            slot = EquipmentSlot(slot_value)
        except ValueError as exc:
            raise ValueError("Unknown equipment slot.") from exc

        if slot not in PLAYABLE_EQUIPMENT_SLOTS:
            raise ValueError("Legacy outfit slot is not editable in Equipment v2.")

        if item_instance_id is None:
            self.service.unequip(
                character_asset_id=character_id,
                slot=slot,
            )
            return self.get_state(character_id)

        if not isinstance(item_instance_id, str) or not item_instance_id.strip():
            raise ValueError("item_instance_id must be a non-empty string or null.")

        collection = self.service.ensure_starter_collection()
        item = collection.item_by_id(item_instance_id)
        if item is None:
            raise ValueError("Equipment item is not owned.")

        definition = self.service.get_definition(item.definition_id)
        if definition.slot != slot:
            raise ValueError("Equipment item does not belong to this slot.")

        self.service.equip(
            character_asset_id=character_id,
            item_instance_id=item_instance_id,
        )
        return self.get_state(character_id)
