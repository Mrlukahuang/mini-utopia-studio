"""Bounded, canonical primitive compositions made privately by a child.

Only geometric instructions are accepted; no URLs, file paths, scripts, shader
source, arbitrary meshes or executable payloads can be submitted by a browser.
The same immutable specification can be consumed by play and movie renderers.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FamilyPrimitivePart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shape: Literal["box", "sphere", "cylinder"]
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: tuple[float, float, float] = (0.5, 0.5, 0.5)
    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    rotation_y_degrees: float = Field(default=0.0, ge=-180.0, le=180.0)

    @field_validator("position", "size")
    @classmethod
    def bounded_vectors(cls, value: tuple[float, float, float], info):
        if not all(math.isfinite(x) for x in value):
            raise ValueError("Vectors must contain finite numbers")
        if info.field_name == "position" and any(abs(x) > 4 for x in value):
            raise ValueError("Parts must remain within a four-metre envelope")
        if info.field_name == "size" and any(x < 0.05 or x > 3 for x in value):
            raise ValueError("Part dimensions must be between 0.05 and 3 metres")
        return value

    @field_validator("rotation_y_degrees")
    @classmethod
    def finite_rotation(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Rotation must be finite")
        return value


class FamilyCompositionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["prop", "wearable"]
    display_name: str = Field(min_length=1, max_length=48)
    slot: Literal["headwear", "accessory", "backpack", "top"] | None = None
    parts: list[FamilyPrimitivePart] = Field(min_length=1, max_length=12)

    @field_validator("display_name")
    @classmethod
    def visible_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("A visible asset name is required")
        return name

    @model_validator(mode="after")
    def valid_slot(self):
        if (self.kind == "wearable") != (self.slot is not None):
            raise ValueError("Wearables require a supported slot; props have no slot")
        return self
