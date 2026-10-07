from datetime import datetime
from pydantic import BaseModel, Field
from studio.core.enums import ReviewStatus, StoryMode
from studio.models.asset import now_utc


class DialogueLine(BaseModel):
    character_asset_id: str
    text: str
    emotion: str = ""


class Shot(BaseModel):
    shot_id: str
    scene_id: str
    duration_seconds: float = Field(default=3.0, ge=0.5, le=30.0)
    asset_ids: list[str] = Field(default_factory=list)
    shot_type: str = ""
    camera: str = ""
    action: str = ""
    expression: str = ""
    dialogue: list[DialogueLine] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)


class Scene(BaseModel):
    scene_id: str
    title: str = ""
    story_beat: str = ""
    location_asset_id: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    description: str = ""
    action_summary: str = ""
    dialogue_notes: str = ""
    continuity_notes: list[str] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)


class Episode(BaseModel):
    episode_id: str
    universe_id: str | None = None
    story_id: str
    title: str
    mode: StoryMode = StoryMode.PLAYGROUND
    asset_ids: list[str] = Field(default_factory=list)
    world_asset_id: str | None = None
    active_baby_id: str | None = None
    continuity_memory_ids: list[str] = Field(default_factory=list)
    status: ReviewStatus = ReviewStatus.DRAFT
    scenes: list[Scene] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
