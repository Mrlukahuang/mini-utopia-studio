from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from studio.models.asset import now_utc


StoryboardFrameStatus = Literal["missing", "ready", "stale", "failed"]
StoryboardReviewStatus = Literal["unreviewed", "approved", "needs_change"]


class StoryboardFrameRecord(BaseModel):
    """Derived visual planning frame for one production Shot."""

    episode_id: str
    scene_id: str
    shot_id: str
    source_fingerprint: str
    status: StoryboardFrameStatus = "missing"
    frame_path: str
    capture_time_seconds: float = Field(ge=0.0)
    camera_summary: str = ""
    blocking_summary: str = ""
    generated_at: datetime | None = None
    error: str = ""
    review_status: StoryboardReviewStatus = "unreviewed"
    review_note: str = ""
    review_source_fingerprint: str = ""
    reviewed_at: datetime | None = None

    @property
    def current(self) -> bool:
        return self.status == "ready"

    @property
    def approved_current(self) -> bool:
        return bool(
            self.status == "ready"
            and self.review_status == "approved"
            and self.review_source_fingerprint == self.source_fingerprint
        )
