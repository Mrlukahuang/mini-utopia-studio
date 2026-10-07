from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from studio.models.asset import now_utc


class UniverseMemoryKind(str, Enum):
    CANON_STORY = "canon_story"
    WORLD_DISCOVERY = "world_discovery"
    ITEM_ACQUIRED = "item_acquired"
    BABY_MILESTONE = "baby_milestone"
    RELATIONSHIP = "relationship"
    PORTAL_UNLOCK = "portal_unlock"
    LORE = "lore"


def memory_id_for_source(universe_id: str, source_key: str) -> str:
    digest = hashlib.sha256(
        f"{universe_id}|{source_key}".encode("utf-8")
    ).hexdigest()[:20].upper()
    return f"MEM_{digest}"


class UniverseMemoryRecord(BaseModel):
    memory_id: str
    universe_id: str = Field(min_length=1)
    source_key: str = Field(min_length=1)
    kind: UniverseMemoryKind
    summary: str = Field(min_length=1, max_length=1200)
    asset_ids: list[str] = Field(default_factory=list)
    story_id: str | None = None
    world_asset_id: str | None = None
    baby_id: str | None = None
    item_instance_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    @classmethod
    def create(
        cls,
        *,
        universe_id: str,
        source_key: str,
        kind: UniverseMemoryKind,
        summary: str,
        **kwargs,
    ) -> "UniverseMemoryRecord":
        return cls(
            memory_id=memory_id_for_source(universe_id, source_key),
            universe_id=universe_id,
            source_key=source_key,
            kind=kind,
            summary=summary,
            **kwargs,
        )
