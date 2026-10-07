from __future__ import annotations

from pydantic import BaseModel, Field


class StoryBeatSuggestions(BaseModel):
    arrive: str = Field(min_length=1, max_length=500)
    discover: str = Field(min_length=1, max_length=500)
    problem: str = Field(min_length=1, max_length=500)
    adventure: str = Field(min_length=1, max_length=500)
    surprise: str = Field(min_length=1, max_length=500)
    portal: str = Field(min_length=1, max_length=500)
