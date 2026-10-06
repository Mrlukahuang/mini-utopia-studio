from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from studio.models.avatar import AVATAR_RIG_FAMILY, BodyType, avatar_socket_names
from studio.models.equipment import EquipmentRarity, EquipmentSlot, StatBlock


EQUIPMENT_RUNTIME_SCHEMA_VERSION = "1.0"


class EquipmentRuntimeItemSpec(BaseModel):
    item_instance_id: str
    definition_id: str
    display_name: str
    slot: EquipmentSlot
    rarity: EquipmentRarity
    mesh_asset_id: str | None = None
    animation_class: str | None = None
    rolled_stats: StatBlock = Field(default_factory=StatBlock)


class EquipmentRuntimeSpec(BaseModel):
    schema_version: str = EQUIPMENT_RUNTIME_SCHEMA_VERSION
    character_asset_id: str
    rig_family: str = AVATAR_RIG_FAMILY
    body_type: BodyType = BodyType.STANDARD
    socket_names: tuple[str, ...] = Field(default_factory=avatar_socket_names)
    final_stats: StatBlock = Field(default_factory=StatBlock)
    equipped: dict[str, EquipmentRuntimeItemSpec] = Field(default_factory=dict)

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            self.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return target
