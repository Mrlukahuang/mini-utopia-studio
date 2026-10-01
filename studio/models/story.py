from datetime import datetime
from pydantic import BaseModel, Field
from studio.core.enums import StoryMode, ReviewStatus
from studio.models.asset import now_utc


class Story(BaseModel):
    story_id: str
    title: str
    premise: str
    mode: StoryMode = StoryMode.PLAYGROUND
    universe_id: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    hook: str = ""
    conflict: str = ""
    twist: str = ""
    ending: str = ""
    status: ReviewStatus = ReviewStatus.DRAFT
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
