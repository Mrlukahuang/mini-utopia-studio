from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from studio.core.ids import new_id
from studio.models.asset import now_utc


BABY_SCHEMA_VERSION = "1.0"


class BabyGrowthStage(str, Enum):
    BABY = "baby"


class BabyCompanion(BaseModel):
    """Persistent companion identity owned by the creator, not by a Character."""

    schema_version: str = BABY_SCHEMA_VERSION
    baby_id: str
    display_name: str
    species_id: str
    appearance_seed: str

    growth_stage: BabyGrowthStage = BabyGrowthStage.BABY
    level: int = Field(default=1, ge=1)
    xp: int = Field(default=0, ge=0)
    bond: int = Field(default=0, ge=0)
    active: bool = False

    cosmetic_item_ids: list[str] = Field(default_factory=list)
    ability_ids: list[str] = Field(default_factory=list)
    stat_modifiers: dict[str, int | float | str] = Field(default_factory=dict)
    evolution_metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class BabyRoster(BaseModel):
    """Creator-owned Baby companions plus the stable active-companion pointer."""

    roster_id: str = "BABIES_DEFAULT"
    owner_key: str = "default_creator"
    babies: list[BabyCompanion] = Field(default_factory=list)
    active_baby_id: str | None = None
    updated_at: datetime = Field(default_factory=now_utc)

    @model_validator(mode="after")
    def validate_identity(self) -> "BabyRoster":
        ids = [baby.baby_id for baby in self.babies]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate baby_id in BabyRoster.")
        if self.active_baby_id is not None and self.active_baby_id not in set(ids):
            raise ValueError("active_baby_id must reference an owned Baby.")
        active_flags = [baby.baby_id for baby in self.babies if baby.active]
        if len(active_flags) > 1:
            raise ValueError("Only one Baby can be active.")
        if active_flags and self.active_baby_id != active_flags[0]:
            raise ValueError("active Baby flag must match active_baby_id.")
        return self

    def baby_by_id(self, baby_id: str) -> BabyCompanion | None:
        return next((baby for baby in self.babies if baby.baby_id == baby_id), None)

    def active_baby(self) -> BabyCompanion | None:
        if not self.active_baby_id:
            return None
        return self.baby_by_id(self.active_baby_id)


class BabyRuntimeSpec(BaseModel):
    """Small Godot-facing hook reserved for the later companion follow runtime."""

    baby_id: str
    display_name: str
    species_id: str
    appearance_seed: str
    growth_stage: BabyGrowthStage
    level: int
    active: bool
    cosmetic_item_ids: list[str] = Field(default_factory=list)
    follow_enabled: bool = True

    def save_json(self, target_path: str | Path) -> Path:
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path


def create_baby_companion(
    *,
    display_name: str,
    species_id: str,
) -> BabyCompanion:
    baby_id = new_id("BABY")
    return BabyCompanion(
        baby_id=baby_id,
        display_name=display_name.strip(),
        species_id=species_id,
        appearance_seed=new_id("BSEED"),
    )
