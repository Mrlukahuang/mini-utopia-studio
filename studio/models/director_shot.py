from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from studio.models.episode import Shot
from studio.models.play_session import PlaySessionRuntimeSpec


DIRECTOR_SHOT_SCHEMA_VERSION = "1.0"


class DirectorCameraSpec(BaseModel):
    position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    fov: float = Field(default=48.0, ge=20.0, le=100.0)
    movement: str = ""
    end_position: tuple[float, float, float] | None = None
    end_look_at: tuple[float, float, float] | None = None
    end_fov: float | None = Field(default=None, ge=20.0, le=100.0)
    movement_mode: Literal[
        "hold",
        "push_in",
        "pull_back",
        "pan",
        "follow",
        "reveal",
    ] = "hold"
    easing: Literal["linear", "smooth"] = "smooth"


class DirectorShotSession(BaseModel):
    """One executable Episode Shot plus the exact reusable runtime state."""

    schema_version: str = DIRECTOR_SHOT_SCHEMA_VERSION
    director_session_id: str
    source_fingerprint: str

    episode_id: str
    scene_id: str
    shot_id: str
    story_id: str

    world_asset_id: str | None = None
    character_asset_id: str
    scene_title: str = ""
    story_beat: str = ""

    duration_seconds: float = Field(ge=0.5, le=30.0)
    animation_intent: Literal["idle", "walk", "run", "attack"] = "idle"
    camera: DirectorCameraSpec
    shot: Shot
    play_session: PlaySessionRuntimeSpec

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return target
