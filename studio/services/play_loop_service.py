from __future__ import annotations

from pathlib import Path

from studio.core.enums import AssetType, ReviewStatus
from studio.models.equipment import (
    EquipmentSlot,
    PLAYABLE_EQUIPMENT_SLOTS,
)
from studio.models.play_loop import FirstAdventureStatus
from studio.models.play_session import PlaySessionRuntimeSpec
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.combat_drop_service import (
    CombatDropService,
    DEFAULT_COMBAT_DROP_INBOX_PATH,
)
from studio.services.equipment_service import EquipmentService
from studio.services.play_session_service import DEFAULT_GODOT_PLAY_SESSION_PATH


BONE_BUCKLER_SLUG = "reward_bone_buckler"


class FirstPlayLoopService:
    """Derive child-visible adventure progress from canonical saved state."""

    def __init__(
        self,
        repository: StudioRepository,
        *,
        equipment: EquipmentService | None = None,
        babies: BabyService | None = None,
        play_session_path: str | Path | None = None,
        combat_inbox_path: str | Path | None = None,
    ):
        self.repository = repository
        self.equipment = equipment or EquipmentService(repository)
        self.babies = babies or BabyService(repository)
        self.play_session_path = Path(
            play_session_path or DEFAULT_GODOT_PLAY_SESSION_PATH
        )
        self.combat_inbox_path = Path(
            combat_inbox_path or DEFAULT_COMBAT_DROP_INBOX_PATH
        )

    def status(
        self,
        *,
        preferred_character_id: str | None = None,
    ) -> FirstAdventureStatus:
        session = self._read_session()
        character = self._select_character(
            preferred_character_id=preferred_character_id,
            session=session,
        )
        if character is None:
            return FirstAdventureStatus()

        collection = self.equipment.ensure_starter_collection()
        definitions = self.equipment.list_definitions()
        loadout = collection.loadout_for(character.asset_id)

        equipped_ids = {
            loadout.item_id_for_slot(slot)
            for slot in PLAYABLE_EQUIPMENT_SLOTS
        }
        equipped_ids.discard(None)

        reward_asset = next(
            (
                asset
                for asset in self.repository.list_assets(AssetType.EQUIPMENT)
                if asset.slug == BONE_BUCKLER_SLUG
            ),
            None,
        )
        reward_definition_id = (
            reward_asset.asset_id
            if reward_asset is not None
            else None
        )
        owned_reward_ids = {
            item.item_instance_id
            for item in collection.items
            if item.definition_id == reward_definition_id
        }

        reward_equipped = (
            loadout.weapon_offhand_item_id in owned_reward_ids
            if owned_reward_ids
            else False
        )

        session_matches = (
            session is not None
            and session.character_asset_id == character.asset_id
            and session.world_asset_id is not None
        )
        stronger_session_ready = False
        if session_matches and reward_definition_id is not None:
            offhand = session.equipment.equipped.get(
                EquipmentSlot.WEAPON_OFFHAND.value
            )
            stronger_session_ready = bool(
                offhand is not None
                and offhand.definition_id == reward_definition_id
            )

        pending = CombatDropService(
            self.repository,
            inbox_path=self.combat_inbox_path,
            equipment=self.equipment,
        ).read_inbox()
        pending_bone_drop = any(
            drop.definition_slug == BONE_BUCKLER_SLUG
            and drop.drop_id not in set(collection.claimed_drop_ids)
            for drop in pending.drops
        )

        return FirstAdventureStatus(
            character_asset_id=character.asset_id,
            character_name=character.display_name,
            character_ready=True,
            baby_ready=self.babies.active_baby() is not None,
            loadout_ready=bool(equipped_ids),
            play_session_ready=session_matches,
            reward_waiting=pending_bone_drop,
            reward_claimed=bool(owned_reward_ids),
            reward_equipped=reward_equipped,
            stronger_session_ready=stronger_session_ready,
        )

    def _select_character(
        self,
        *,
        preferred_character_id: str | None,
        session: PlaySessionRuntimeSpec | None,
    ):
        candidates = [
            asset
            for asset in self.repository.list_assets(AssetType.CHARACTER)
            if asset.status != ReviewStatus.ARCHIVED
            and "character_profile" in asset.metadata
        ]
        if not candidates:
            return None

        wanted = preferred_character_id
        if wanted is None and session is not None:
            wanted = session.character_asset_id
        if wanted is not None:
            match = next(
                (asset for asset in candidates if asset.asset_id == wanted),
                None,
            )
            if match is not None:
                return match
        return candidates[0]

    def _read_session(self) -> PlaySessionRuntimeSpec | None:
        if not self.play_session_path.exists():
            return None
        text = self.play_session_path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        try:
            return PlaySessionRuntimeSpec.model_validate_json(text)
        except Exception:
            return None
