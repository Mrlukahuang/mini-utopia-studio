from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from studio.models.avatar import AVATAR_RIG_FAMILY, BodyType, avatar_socket_names


class RuntimeAnimationSpec(BaseModel):
    idle: str = "Idle"
    walk: str = "Walk"
    run: str = "Run"


class CharacterRuntimeSpec(BaseModel):
    """Renderer-facing Character 3D contract.

    Canon CharacterProfile stays provider/runtime agnostic. The runtime spec
    translates it into a replaceable procedural-or-GLB presentation contract.
    """

    mode: Literal["procedural", "glb"] = "procedural"
    model_data_uri: str | None = None

    rig_family: str = AVATAR_RIG_FAMILY
    body_type: BodyType = BodyType.STANDARD
    socket_names: tuple[str, ...] = Field(default_factory=avatar_socket_names)

    species_head_id: str = "species_head_human_v1"
    surface_type: str = "skin"
    surface_color_hex: str = "#F2C7A5"
    eye_style_id: str = "eyes_round_soft_v1"
    hair_style_id: str = "hair_none"
    scale: float = Field(default=1.0, gt=0, le=10)
    animation_clips: RuntimeAnimationSpec = Field(default_factory=RuntimeAnimationSpec)

    body_color_hex: str = "#FFF4D7"
    accent_color_hex: str = "#B9E7D0"
    hair_color_hex: str = "#5B4036"
    eye_color_hex: str = "#7A5238"

    playable_height_units: float = Field(default=3.4, gt=1, le=8)
    head_to_body_ratio: float = Field(default=0.34, gt=0.2, lt=0.5)
