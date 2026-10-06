from __future__ import annotations

from pathlib import Path

from studio.core.enums import AssetType
from studio.models.combat_drop import (
    CombatDropClaim,
    CombatDropInbox,
)
from studio.models.equipment import create_equipment_instance
from studio.repositories.base import StudioRepository
from studio.services.equipment_service import EquipmentService
from studio.models.asset import now_utc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMBAT_DROP_INBOX_PATH = (
    PROJECT_ROOT
    / "godot"
    / "runtime_state"
    / "combat_drop_inbox.json"
)


class CombatDropService:
    """Claim Godot combat receipts into the persistent Creator Collection."""

    def __init__(
        self,
        repository: StudioRepository,
        *,
        inbox_path: str | Path | None = None,
        equipment: EquipmentService | None = None,
    ):
        self.repository = repository
        self.inbox_path = (
            Path(inbox_path)
            if inbox_path is not None
            else DEFAULT_COMBAT_DROP_INBOX_PATH
        )
        self.equipment = equipment or EquipmentService(repository)

    def read_inbox(self) -> CombatDropInbox:
        if not self.inbox_path.exists():
            return CombatDropInbox()
        text = self.inbox_path.read_text(encoding="utf-8").strip()
        if not text:
            return CombatDropInbox()
        return CombatDropInbox.model_validate_json(text)

    def claim_available(self) -> list[CombatDropClaim]:
        inbox = self.read_inbox()
        if not inbox.drops:
            return []

        self.equipment.ensure_default_definitions()
        assets_by_slug = {
            asset.slug: asset
            for asset in self.repository.list_assets(AssetType.EQUIPMENT)
            if asset.metadata.get("equipment_definition")
        }
        collection = self.equipment.ensure_starter_collection()
        claimed = set(collection.claimed_drop_ids)
        results: list[CombatDropClaim] = []

        for receipt in inbox.drops:
            if receipt.drop_id in claimed:
                continue

            asset = assets_by_slug.get(receipt.definition_slug)
            if asset is None:
                # Keep the receipt unclaimed so a later definition sync can
                # recover it rather than silently destroying the reward.
                continue

            definition = self.equipment.get_definition(asset.asset_id)
            item = create_equipment_instance(
                definition=definition,
                rarity=receipt.rarity,
                item_level=receipt.item_level,
                generation_seed=receipt.generation_seed,
            )
            collection.items.append(item)
            collection.claimed_drop_ids.append(receipt.drop_id)
            claimed.add(receipt.drop_id)
            results.append(
                CombatDropClaim(
                    drop_id=receipt.drop_id,
                    item_instance_id=item.item_instance_id,
                    display_name=definition.display_name,
                    rarity=item.rarity,
                    slot=definition.slot,
                )
            )

        if results:
            collection.updated_at = now_utc()
            self.repository.save_collection(collection)

        return results
