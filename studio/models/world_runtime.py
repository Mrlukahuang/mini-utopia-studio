from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


WORLD_RUNTIME_BINDING_SCHEMA_VERSION = "1.0"


class GodotWorldSceneBinding(BaseModel):
    """Stable Creator World -> Godot scene contract."""

    schema_version: str = WORLD_RUNTIME_BINDING_SCHEMA_VERSION
    world_asset_id: str = Field(min_length=1)
    scene_path: str = Field(min_length=1)
    scene_label: str = ""
    source: Literal["system_builtin", "creator", "migration"] = "creator"
    playable: bool = True

    @field_validator("scene_path")
    @classmethod
    def validate_scene_path(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("res://"):
            raise ValueError("Godot scene_path must start with res://")
        if not cleaned.endswith(".tscn"):
            raise ValueError("Godot scene_path must point to a .tscn scene")
        return cleaned
