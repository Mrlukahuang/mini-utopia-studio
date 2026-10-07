from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from studio.core.enums import ReviewStatus
from studio.models.asset import now_utc


class QuestTriggerType(str, Enum):
    IMMEDIATE = "immediate"
    ENTER_LOCATION = "enter_location"
    STORY_BEAT = "story_beat"
    ITEM_OWNED = "item_owned"
    QUEST_COMPLETE = "quest_complete"


class QuestObjectiveType(str, Enum):
    GO_TO_LOCATION = "go_to_location"
    DEFEAT_ENEMY = "defeat_enemy"
    COLLECT_ITEM = "collect_item"
    INTERACT = "interact"
    RETURN_TO_TARGET = "return_to_target"
    OPEN_PORTAL = "open_portal"


class QuestRewardType(str, Enum):
    EQUIPMENT = "equipment"
    BABY_XP = "baby_xp"
    BABY_BOND = "baby_bond"
    UNLOCK = "unlock"


class QuestTrigger(BaseModel):
    trigger_type: QuestTriggerType
    target_id: str | None = None
    required_value: int | str | bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestObjective(BaseModel):
    objective_id: str = Field(min_length=1)
    objective_type: QuestObjectiveType
    label: str = Field(min_length=1)
    target_id: str | None = None
    target_count: int = Field(default=1, ge=1)
    order: int = Field(ge=0)
    optional: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestReward(BaseModel):
    reward_id: str = Field(min_length=1)
    reward_type: QuestRewardType
    target_id: str | None = None
    amount: int = Field(default=1, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestDefinition(BaseModel):
    schema_version: str = "1.0"
    quest_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    world_asset_id: str = Field(min_length=1)
    story_id: str | None = None
    universe_id: str | None = None
    start_triggers: list[QuestTrigger] = Field(
        default_factory=lambda: [
            QuestTrigger(trigger_type=QuestTriggerType.IMMEDIATE)
        ]
    )
    objectives: list[QuestObjective] = Field(min_length=1)
    rewards: list[QuestReward] = Field(default_factory=list)
    repeatable: bool = False
    status: ReviewStatus = ReviewStatus.DRAFT
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def _validate_contract(self) -> "QuestDefinition":
        objective_ids = [item.objective_id for item in self.objectives]
        if len(objective_ids) != len(set(objective_ids)):
            raise ValueError("Quest objective_id values must be unique.")

        orders = [item.order for item in self.objectives]
        if len(orders) != len(set(orders)):
            raise ValueError("Quest objective order values must be unique.")

        reward_ids = [item.reward_id for item in self.rewards]
        if len(reward_ids) != len(set(reward_ids)):
            raise ValueError("Quest reward_id values must be unique.")

        self.objectives.sort(key=lambda item: item.order)
        return self

    def runtime_payload(self) -> dict[str, Any]:
        """Stable JSON-ready contract consumed by future Godot quest runtime."""
        return self.model_dump(mode="json")
