from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from studio.core.ids import new_id
from studio.models.asset import now_utc
from studio.models.baby import BabyRuntimeSpec
from studio.models.equipment_runtime import EquipmentRuntimeSpec
from studio.models.runtime_character import CharacterRuntimeSpec
from studio.models.quest import QuestDefinition
from studio.models.world_gameplay import WorldGameplayLayer
from studio.models.world_creative import WorldCreativeLayout
from studio.models.world_runtime import GodotWorldSceneBinding


PLAY_SESSION_SCHEMA_VERSION = "1.0"


class PlaySessionRuntimeSpec(BaseModel):
    """Single Creator -> game runtime payload.

    Character appearance, Equipment loadout/stats and Active Baby stay separate
    canonical models but travel together so renderers never reconstruct state.
    """

    schema_version: str = PLAY_SESSION_SCHEMA_VERSION
    session_id: str = Field(default_factory=lambda: new_id("PLAY"))
    source: str = "creator"

    character_asset_id: str
    character_name: str
    character: CharacterRuntimeSpec
    equipment: EquipmentRuntimeSpec
    baby: BabyRuntimeSpec | None = None
    quest: QuestDefinition | None = None
    world_gameplay: WorldGameplayLayer | None = None
    creative_layout: WorldCreativeLayout | None = None
    world_runtime: GodotWorldSceneBinding | None = None

    world_asset_id: str | None = None
    world_name: str | None = None
    created_at: datetime = Field(default_factory=now_utc)

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return target
