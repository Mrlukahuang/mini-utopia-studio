from __future__ import annotations

from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import now_utc
from studio.models.equipment import (
    EquipmentRarity,
    create_equipment_instance,
)
from studio.models.quest import QuestRewardType
from studio.models.quest_reward import (
    QuestBabyRewardClaim,
    QuestRewardClaim,
    QuestRewardInbox,
)
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEST_REWARD_INBOX_PATH = (
    PROJECT_ROOT
    / "godot"
    / "runtime_state"
    / "quest_reward_inbox.json"
)


class QuestRewardService:
    """Claim generic Quest rewards into durable Creator state.

    Godot only reports that a Quest completed. Reward definitions are resolved
    again from the persisted QuestDefinition so runtime clients cannot choose
    their own rarity/stats.
    """

    def __init__(
        self,
        repository: StudioRepository,
        *,
        inbox_path: str | Path | None = None,
        equipment: EquipmentService | None = None,
        babies: BabyService | None = None,
    ):
        self.repository = repository
        self.inbox_path = (
            Path(inbox_path)
            if inbox_path is not None
            else DEFAULT_QUEST_REWARD_INBOX_PATH
        )
        self.equipment = equipment or EquipmentService(repository)
        self.babies = babies or BabyService(repository)

    def read_inbox(self) -> QuestRewardInbox:
        if not self.inbox_path.exists():
            return QuestRewardInbox()
        text = self.inbox_path.read_text(encoding="utf-8").strip()
        if not text:
            return QuestRewardInbox()
        return QuestRewardInbox.model_validate_json(text)

    @staticmethod
    def _claim_id(
        *,
        quest_id: str,
        reward_id: str,
        completion_id: str,
        repeatable: bool,
    ) -> str:
        if repeatable:
            return f"{completion_id}:{reward_id}"
        return f"{quest_id}:{reward_id}"

    def claim_baby_growth(self) -> list[QuestBabyRewardClaim]:
        """Apply BABY_XP/BABY_BOND rewards to the current Active Baby.

        If no Active Baby exists, rewards remain unclaimed so they can recover
        after the creator chooses an Initial Baby.
        """

        inbox = self.read_inbox()
        if not inbox.completions:
            return []

        active = self.babies.active_baby()
        if active is None:
            return []

        collection = self.equipment.ensure_starter_collection()
        claimed = set(collection.claimed_quest_reward_ids)
        results: list[QuestBabyRewardClaim] = []

        for completion in inbox.completions:
            quest = self.repository.get_quest(completion.quest_id)
            if quest is None:
                continue

            for reward in quest.rewards:
                if reward.reward_type not in {
                    QuestRewardType.BABY_XP,
                    QuestRewardType.BABY_BOND,
                }:
                    continue

                claim_id = self._claim_id(
                    quest_id=quest.quest_id,
                    reward_id=reward.reward_id,
                    completion_id=completion.completion_id,
                    repeatable=quest.repeatable,
                )
                if claim_id in claimed:
                    continue

                current = self.babies.active_baby()
                if current is None:
                    continue

                if reward.reward_type == QuestRewardType.BABY_XP:
                    self.babies.add_xp(
                        baby_id=current.baby_id,
                        amount=reward.amount,
                    )
                else:
                    self.babies.add_bond(
                        baby_id=current.baby_id,
                        amount=reward.amount,
                    )

                updated = self.babies.active_baby()
                if updated is None:
                    continue

                collection.claimed_quest_reward_ids.append(claim_id)
                claimed.add(claim_id)
                results.append(
                    QuestBabyRewardClaim(
                        claim_id=claim_id,
                        completion_id=completion.completion_id,
                        quest_id=quest.quest_id,
                        reward_id=reward.reward_id,
                        reward_type=reward.reward_type,
                        baby_id=updated.baby_id,
                        baby_name=updated.display_name,
                        amount=reward.amount,
                        level=updated.level,
                        xp=updated.xp,
                        bond=updated.bond,
                    )
                )

        if results:
            collection.updated_at = now_utc()
            self.repository.save_collection(collection)

        return results


    def claim_available(self) -> list[QuestRewardClaim]:
        inbox = self.read_inbox()
        if not inbox.completions:
            return []

        self.equipment.ensure_default_definitions()
        assets_by_slug = {
            asset.slug: asset
            for asset in self.repository.list_assets(AssetType.EQUIPMENT)
            if asset.metadata.get("equipment_definition")
        }
        collection = self.equipment.ensure_starter_collection()
        claimed = set(collection.claimed_quest_reward_ids)
        results: list[QuestRewardClaim] = []

        for completion in inbox.completions:
            quest = self.repository.get_quest(completion.quest_id)
            if quest is None:
                # Keep unknown receipts unclaimed so they can recover after a
                # later repository sync instead of being silently discarded.
                continue

            for reward in quest.rewards:
                if reward.reward_type != QuestRewardType.EQUIPMENT:
                    # BB-02 and later systems execute the other generic reward
                    # types from this same durable completion receipt.
                    continue
                if not reward.target_id:
                    continue

                asset = assets_by_slug.get(reward.target_id)
                if asset is None:
                    continue
                definition = self.equipment.get_definition(asset.asset_id)

                try:
                    rarity = EquipmentRarity(
                        str(reward.metadata.get("rarity", "green"))
                    )
                    item_level = max(
                        1,
                        int(reward.metadata.get("item_level", 1)),
                    )
                except (TypeError, ValueError):
                    # Invalid authored reward metadata must not break My Stuff.
                    # Leave it unclaimed so corrected Quest data can recover.
                    continue

                for unit_index in range(reward.amount):
                    reward_unit_id = (
                        reward.reward_id
                        if reward.amount == 1
                        else f"{reward.reward_id}:{unit_index + 1}"
                    )
                    claim_id = self._claim_id(
                        quest_id=quest.quest_id,
                        reward_id=reward_unit_id,
                        completion_id=completion.completion_id,
                        repeatable=quest.repeatable,
                    )
                    if claim_id in claimed:
                        continue

                    seed = f"QUEST_REWARD::{claim_id}"
                    item = create_equipment_instance(
                        definition=definition,
                        rarity=rarity,
                        item_level=item_level,
                        generation_seed=seed,
                    )
                    collection.items.append(item)
                    collection.claimed_quest_reward_ids.append(claim_id)
                    claimed.add(claim_id)
                    results.append(
                        QuestRewardClaim(
                            claim_id=claim_id,
                            completion_id=completion.completion_id,
                            quest_id=quest.quest_id,
                            reward_id=reward.reward_id,
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
