from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SubtitleCueStatus = Literal["ready", "stale"]


class SubtitleCue(BaseModel):
    cue_id: str = Field(min_length=1)
    source_audio_line_id: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=1)
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(gt=0.0)
    text: str = Field(min_length=1, max_length=1600)
    speaker_label: str = ""
    approved: bool = False
    source: Literal["generated", "creator"] = "generated"

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


class SubtitleTrackSummary(BaseModel):
    cue_count: int = 0
    ready_count: int = 0
    stale_count: int = 0
    approved_count: int = 0
