from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ShotRenderStatus = Literal[
    "missing",
    "rendering",
    "rendered",
    "stale",
    "failed",
]


class ShotRenderRecord(BaseModel):
    episode_id: str
    scene_id: str
    shot_id: str
    source_fingerprint: str
    storyboard_approval_fingerprint: str
    status: ShotRenderStatus = "missing"
    video_path: str
    duration_seconds: float = Field(gt=0.0)
    fps: int = Field(default=24, ge=1, le=120)
    width: int = Field(default=960, ge=160, le=7680)
    height: int = Field(default=540, ge=90, le=4320)
    frame_count: int = Field(default=0, ge=0)
    generated_at: datetime | None = None
    error: str = ""

    @property
    def resolution(self) -> str:
        return f"{self.width}×{self.height}"
