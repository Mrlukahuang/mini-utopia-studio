from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


EpisodeAssemblyStatus = Literal[
    "missing",
    "assembling",
    "ready",
    "stale",
    "failed",
]


class EpisodeAssemblyClip(BaseModel):
    scene_id: str
    shot_id: str
    source_fingerprint: str
    video_path: str
    start_seconds: float = Field(ge=0.0)
    duration_seconds: float = Field(gt=0.0)


class EpisodeAssemblyRecord(BaseModel):
    episode_id: str
    source_fingerprint: str
    status: EpisodeAssemblyStatus = "missing"
    video_path: str
    manifest_path: str
    subtitle_srt_path: str = ""
    clip_count: int = 0
    total_duration_seconds: float = Field(default=0.0, ge=0.0)
    clips: list[EpisodeAssemblyClip] = Field(default_factory=list)
    audio_line_ids: list[str] = Field(default_factory=list)
    subtitle_cue_ids: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None
    error: str = ""
