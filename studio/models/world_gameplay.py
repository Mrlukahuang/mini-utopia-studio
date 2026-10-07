from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from studio.models.asset import now_utc


WORLD_GAMEPLAY_SCHEMA_VERSION = "1.0"


class WorldExperienceMode(str, Enum):
    EXPLORE = "explore"
    QUEST = "quest"
    STORY_PLAY = "story_play"


class WorldGameplayTarget(BaseModel):
    target_id: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    position: tuple[float, float, float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorldGameplayLayer(BaseModel):
    schema_version: str = WORLD_GAMEPLAY_SCHEMA_VERSION
    world_asset_id: str = Field(min_length=1)
    modes: list[WorldExperienceMode] = Field(
        default_factory=lambda: [WorldExperienceMode.EXPLORE]
    )
    quest_ids: list[str] = Field(default_factory=list)
    story_ids: list[str] = Field(default_factory=list)
    targets: list[WorldGameplayTarget] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def _normalize_unique_values(self) -> "WorldGameplayLayer":
        self.modes = list(dict.fromkeys(self.modes))
        self.quest_ids = list(dict.fromkeys(self.quest_ids))
        self.story_ids = list(dict.fromkeys(self.story_ids))

        target_ids = [target.target_id for target in self.targets]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("World gameplay target_id values must be unique.")
        return self

    def supports(self, mode: WorldExperienceMode) -> bool:
        return mode in self.modes
