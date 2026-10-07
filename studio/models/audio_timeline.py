from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AudioSpeakerKind = Literal["character", "narrator"]
AudioLineSource = Literal["generated", "creator"]


class EpisodeAudioLine(BaseModel):
    line_id: str = Field(min_length=1)
    scene_id: str
    shot_id: str
    speaker_kind: AudioSpeakerKind
    speaker_asset_id: str | None = None
    text: str = Field(min_length=1, max_length=1200)
    start_seconds: float = Field(ge=0.0)
    duration_seconds: float = Field(ge=0.2, le=60.0)
    emotion: str = ""
    delivery_note: str = ""
    source: AudioLineSource = "generated"
    approved: bool = False

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds


class AudioTimelineSummary(BaseModel):
    line_count: int = 0
    approved_count: int = 0
    total_spoken_seconds: float = 0.0
    episode_end_seconds: float = 0.0
    overlap_line_ids: list[str] = Field(default_factory=list)
