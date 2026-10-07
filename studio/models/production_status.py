from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ProductionNextAction = Literal[
    "build_scenes",
    "build_shots",
    "generate_storyboard",
    "review_storyboard",
    "render_shots",
    "assemble_episode",
    "complete",
]


class EpisodeProductionStatus(BaseModel):
    episode_id: str
    story_ready: bool = False

    scenes_ready: int = 0
    scenes_total: int = 0

    shots_ready: int = 0
    shots_total: int = 0

    storyboard_ready: int = 0
    storyboard_approved: int = 0
    storyboard_needs_change: int = 0
    storyboard_stale: int = 0

    rendered_shots: int = 0
    final_package_ready: bool = False

    next_action: ProductionNextAction
    progress_percent: int = Field(ge=0, le=100)

    @property
    def storyboard_total(self) -> int:
        return self.shots_total
