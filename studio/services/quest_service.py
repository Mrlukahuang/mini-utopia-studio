from __future__ import annotations

from studio.core.enums import AssetType, ReviewStatus
from studio.core.ids import new_id
from studio.models.quest import (
    QuestDefinition,
    QuestObjective,
    QuestObjectiveType,
    QuestReward,
    QuestRewardType,
    QuestTrigger,
    QuestTriggerType,
)
from studio.repositories.base import StudioRepository


class QuestService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def create_quest(
        self,
        *,
        title: str,
        world_asset_id: str,
        objectives: list[QuestObjective],
        description: str = "",
        story_id: str | None = None,
        universe_id: str | None = None,
        start_triggers: list[QuestTrigger] | None = None,
        rewards: list[QuestReward] | None = None,
        repeatable: bool = False,
        status: ReviewStatus = ReviewStatus.DRAFT,
    ) -> QuestDefinition:
        world = self.repository.get_asset(world_asset_id)
        if world is None:
            raise ValueError(f"Unknown Quest world_asset_id: {world_asset_id}")
        if world.asset_type != AssetType.LOCATION:
            raise ValueError("Quest world_asset_id must reference a Location asset.")

        if story_id is not None and self.repository.get_story(story_id) is None:
            raise ValueError(f"Unknown Quest story_id: {story_id}")

        quest = QuestDefinition(
            quest_id=new_id("QUEST"),
            title=title.strip(),
            description=description.strip(),
            world_asset_id=world_asset_id,
            story_id=story_id,
            universe_id=universe_id,
            start_triggers=(
                start_triggers
                if start_triggers is not None
                else [QuestTrigger(trigger_type=QuestTriggerType.IMMEDIATE)]
            ),
            objectives=objectives,
            rewards=rewards or [],
            repeatable=repeatable,
            status=status,
        )
        self.repository.save_quest(quest)
        return quest

    def get_quest(self, quest_id: str) -> QuestDefinition | None:
        return self.repository.get_quest(quest_id)

    def list_quests(self) -> list[QuestDefinition]:
        return self.repository.list_quests()

    def create_newbie_village_training_quest(
        self,
        *,
        world_asset_id: str,
        story_id: str | None = None,
        universe_id: str | None = None,
    ) -> QuestDefinition:
        """Reference GP-03 proof: authored entirely as Quest data."""
        return self.create_quest(
            title="First Skeleton Adventure / 第一次骷髅冒险",
            description=(
                "Enter Newbie Village, defeat the Training Skeleton, "
                "claim its reward, then open the Portal."
            ),
            world_asset_id=world_asset_id,
            story_id=story_id,
            universe_id=universe_id,
            start_triggers=[
                QuestTrigger(
                    trigger_type=QuestTriggerType.ENTER_LOCATION,
                    target_id=world_asset_id,
                )
            ],
            objectives=[
                QuestObjective(
                    objective_id="arrive_newbie_village",
                    objective_type=QuestObjectiveType.GO_TO_LOCATION,
                    label="Arrive in Newbie Village",
                    target_id=world_asset_id,
                    order=0,
                ),
                QuestObjective(
                    objective_id="defeat_training_skeleton",
                    objective_type=QuestObjectiveType.DEFEAT_ENEMY,
                    label="Defeat the Training Skeleton",
                    target_id="training_skeleton_01",
                    order=1,
                ),
                QuestObjective(
                    objective_id="claim_bone_buckler",
                    objective_type=QuestObjectiveType.COLLECT_ITEM,
                    label="Claim Bone Buckler",
                    target_id="reward_bone_buckler",
                    order=2,
                ),
                QuestObjective(
                    objective_id="open_newbie_portal",
                    objective_type=QuestObjectiveType.OPEN_PORTAL,
                    label="Open the Portal",
                    target_id="newbie_village_portal",
                    order=3,
                ),
            ],
            rewards=[
                QuestReward(
                    reward_id="first_adventure_baby_bond",
                    reward_type=QuestRewardType.BABY_BOND,
                    amount=5,
                ),
                QuestReward(
                    reward_id="unlock_next_portal",
                    reward_type=QuestRewardType.UNLOCK,
                    target_id="next_world_portal",
                    amount=1,
                ),
            ],
        )
