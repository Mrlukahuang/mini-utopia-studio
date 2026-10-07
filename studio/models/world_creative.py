from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from studio.core.ids import new_id
from studio.models.asset import now_utc


WORLD_CREATIVE_SCHEMA_VERSION = "1.0"


class CreativePropType(str, Enum):
    STAR_LAMP = "star_lamp"
    FLOWER_POT = "flower_pot"
    TOY_BENCH = "toy_bench"
    MINI_FLAG = "mini_flag"
    CLOUD_CUSHION = "cloud_cushion"


CREATIVE_PROP_LABELS: dict[CreativePropType, str] = {
    CreativePropType.STAR_LAMP: "⭐ Star Lamp / 星星灯",
    CreativePropType.FLOWER_POT: "🌷 Flower Pot / 花盆",
    CreativePropType.TOY_BENCH: "🪑 Toy Bench / 玩具长椅",
    CreativePropType.MINI_FLAG: "🚩 Mini Flag / 小旗子",
    CreativePropType.CLOUD_CUSHION: "☁️ Cloud Cushion / 云朵坐垫",
}


class WorldDecoration(BaseModel):
    decoration_id: str = Field(default_factory=lambda: new_id("DECOR"))
    prop_type: CreativePropType
    display_name: str = Field(min_length=1)
    position: tuple[float, float, float]
    rotation_y: float = 0.0
    scale: float = Field(default=1.0, ge=0.5, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class WorldCreativeLayout(BaseModel):
    schema_version: str = WORLD_CREATIVE_SCHEMA_VERSION
    world_asset_id: str = Field(min_length=1)
    decorations: list[WorldDecoration] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def _unique_ids(self) -> "WorldCreativeLayout":
        ids = [item.decoration_id for item in self.decorations]
        if len(ids) != len(set(ids)):
            raise ValueError("Creative decoration IDs must be unique.")
        return self
