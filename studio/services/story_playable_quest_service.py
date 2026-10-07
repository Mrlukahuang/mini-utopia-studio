from __future__ import annotations

from studio.core.enums import AssetType
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
from studio.services.quest_service import QuestService


class StoryPlayableQuestService:
    """Turn structured Story beats into a Quest layer over an existing World.

    GP-04 intentionally uses an explicit first-world template instead of
    pretending prose can magically identify gameplay targets. The Story
    provides meaning/labels; stable target IDs/positions come from the reusable
    gameplay layer.
    """

    def __init__(self, repository: StudioRepository):
        self.repository = repository
        self.quests = QuestService(repository)

    def world_for_story(self, story_id: str) -> str:
        story = self.repository.get_story(story_id)
        if story is None:
            raise ValueError(f"Story not found: {story_id}")

        for asset_id in story.asset_ids:
            asset = self.repository.get_asset(asset_id)
            if asset is not None and asset.asset_type == AssetType.LOCATION:
                return asset.asset_id
        raise ValueError("Story must reference a World / Location asset.")

    def existing_for_story(self, story_id: str) -> QuestDefinition | None:
        for quest in self.repository.list_quests():
            if quest.story_id == story_id:
                return quest
        return None

    def make_playable(self, story_id: str) -> QuestDefinition:
        existing = self.existing_for_story(story_id)
        if existing is not None:
            return existing

        story = self.repository.get_story(story_id)
        if story is None:
            raise ValueError(f"Story not found: {story_id}")
        world_asset_id = self.world_for_story(story_id)

        def beat(text: str, fallback: str) -> str:
            clean = text.strip()
            return clean if clean else fallback

        return self.quests.create_quest(
            title=f"🎮 {story.title}",
            description=story.premise,
            world_asset_id=world_asset_id,
            story_id=story.story_id,
            universe_id=story.universe_id,
            start_triggers=[
                QuestTrigger(
                    trigger_type=QuestTriggerType.ENTER_LOCATION,
                    target_id=world_asset_id,
                )
            ],
            objectives=[
                QuestObjective(
                    objective_id="arrive",
                    objective_type=QuestObjectiveType.GO_TO_LOCATION,
                    label=beat(story.hook, "Arrive in the World"),
                    target_id=world_asset_id,
                    order=0,
                    metadata={"story_beat": "ARRIVE"},
                ),
                QuestObjective(
                    objective_id="discover_clue",
                    objective_type=QuestObjectiveType.INTERACT,
                    label=beat(story.discovery, "Discover the glowing clue"),
                    target_id="newbie_village_story_clue",
                    order=1,
                    metadata={
                        "story_beat": "DISCOVER",
                        "position": [0.0, 0.45, 22.0],
                        "prompt": "✨ Discover · Press E",
                    },
                ),
                QuestObjective(
                    objective_id="face_problem",
                    objective_type=QuestObjectiveType.DEFEAT_ENEMY,
                    label=beat(story.conflict, "Defeat the Training Skeleton"),
                    target_id="training_skeleton_01",
                    order=2,
                    metadata={"story_beat": "PROBLEM"},
                ),
                QuestObjective(
                    objective_id="claim_reward",
                    objective_type=QuestObjectiveType.COLLECT_ITEM,
                    label=beat(
                        story.adventure or story.twist,
                        "Claim the Skeleton reward",
                    ),
                    target_id="reward_bone_buckler",
                    order=3,
                    metadata={"story_beat": "ADVENTURE"},
                ),
                QuestObjective(
                    objective_id="open_portal",
                    objective_type=QuestObjectiveType.OPEN_PORTAL,
                    label=beat(story.ending, "Open the Portal"),
                    target_id="newbie_village_portal",
                    order=4,
                    metadata={
                        "story_beat": "PORTAL",
                        "position": [0.0, 0.45, -30.0],
                        "prompt": "🌀 Portal · Press E",
                    },
                ),
            ],
            rewards=[
                QuestReward(
                    reward_id="story_baby_bond",
                    reward_type=QuestRewardType.BABY_BOND,
                    amount=5,
                ),
                QuestReward(
                    reward_id="story_portal_unlock",
                    reward_type=QuestRewardType.UNLOCK,
                    target_id="next_world_portal",
                    amount=1,
                ),
            ],
        )
