from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PublishPackageStatus = Literal[
    "missing",
    "ready",
    "stale",
    "failed",
]


class PublishPackageRecord(BaseModel):
    episode_id: str
    source_fingerprint: str
    status: PublishPackageStatus = "missing"
    final_video_path: str
    subtitle_srt_path: str
    transcript_path: str
    metadata_path: str
    manifest_path: str
    cover_frame_path: str = ""
    title: str
    description: str = ""
    story_id: str
    world_asset_id: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None
    error: str = ""
