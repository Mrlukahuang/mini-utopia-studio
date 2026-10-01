from datetime import datetime
from pydantic import BaseModel, Field
from studio.core.enums import ReviewStatus
from studio.models.asset import now_utc


class DialogueLine(BaseModel):
    character_asset_id: str
    text: str
    emotion: str = ""


class Shot(BaseModel):
    shot_id: str
    scene_id: str
    duration_seconds: float = 3.0
    asset_ids: list[str] = Field(default_factory=list)
    shot_type: str = ""
    camera: str = ""
    action: str = ""
    expression: str = ""
    dialogue: list[DialogueLine] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)


class Scene(BaseModel):
    scene_id: str
    location_asset_id: str | None = None
    description: str = ""
    shots: list[Shot] = Field(default_factory=list)


class Episode(BaseModel):
    episode_id: str
    universe_id: str
    story_id: str
    title: str
    status: ReviewStatus = ReviewStatus.DRAFT
    scenes: list[Scene] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
