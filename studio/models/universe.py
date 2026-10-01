from datetime import datetime
from pydantic import BaseModel, Field
from studio.models.asset import now_utc


class Universe(BaseModel):
    universe_id: str
    name: str
    tagline: str = ""
    description: str = ""
    canon_rules: list[str] = Field(default_factory=list)
    default_asset_ids: list[str] = Field(default_factory=list)
    traveler_asset_id: str | None = None
    style_asset_id: str | None = None
    story_formula: list[str] = Field(default_factory=list)
    portal_rule: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
