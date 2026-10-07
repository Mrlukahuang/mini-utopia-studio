from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from studio.core.enums import ReviewStatus, StoryMode
from studio.models.asset import now_utc
from studio.models.storyboard import StoryboardFrameRecord
from studio.models.audio_timeline import EpisodeAudioLine
from studio.models.subtitle_track import SubtitleCue


class DialogueLine(BaseModel):
    character_asset_id: str
    text: str
    emotion: str = ""


class ShotBlockingPoint(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ShotBlockingSpec(BaseModel):
    actor_start: ShotBlockingPoint = Field(default_factory=ShotBlockingPoint)
    actor_end: ShotBlockingPoint = Field(default_factory=ShotBlockingPoint)
    facing_degrees: float = 0.0
    baby_offset: ShotBlockingPoint = Field(
        default_factory=lambda: ShotBlockingPoint(x=-0.8, y=0.0, z=1.0)
    )
    movement_style: Literal["hold", "walk", "run"] = "hold"
    source: Literal["generated", "creator"] = "generated"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ShotCameraMotionSpec(BaseModel):
    start_position: ShotBlockingPoint
    end_position: ShotBlockingPoint
    start_look_at: ShotBlockingPoint
    end_look_at: ShotBlockingPoint
    start_fov: float = Field(default=48.0, ge=20.0, le=100.0)
    end_fov: float = Field(default=48.0, ge=20.0, le=100.0)
    movement_mode: Literal[
        "hold",
        "push_in",
        "pull_back",
        "pan",
        "follow",
        "reveal",
    ] = "hold"
    easing: Literal["linear", "smooth"] = "smooth"
    source: Literal["generated", "creator"] = "generated"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PerformanceCue(BaseModel):
    cue_id: str = Field(min_length=1)
    cue_type: Literal[
        "idle",
        "walk",
        "run",
        "attack",
        "look_at",
        "reaction",
        "celebrate",
    ]
    start_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=0.5, ge=0.05, le=30.0)
    intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    target: str = ""
    direction_degrees: float | None = None
    source: Literal["generated", "creator"] = "generated"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


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
    blocking: ShotBlockingSpec | None = None
    camera_motion: ShotCameraMotionSpec | None = None
    performance_cues: list[PerformanceCue] | None = None


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
    storyboard_frames: dict[str, StoryboardFrameRecord] = Field(
        default_factory=dict
    )
    audio_timeline: list[EpisodeAudioLine] = Field(default_factory=list)
    subtitle_track: list[SubtitleCue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
