from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


AVATAR_SCHEMA_VERSION = "1.0"
AVATAR_RIG_FAMILY = "humanoid_kaykit_v1"


class BodyType(str, Enum):
    """The only body-shape variants supported by playable Avatar v1."""

    SLIM = "slim"
    STANDARD = "standard"
    CHUBBY = "chubby"


class AvatarSocket(str, Enum):
    """Stable attachment points shared by every v1 humanoid Avatar."""

    WEAPON_R = "Socket_Weapon_R"
    WEAPON_L = "Socket_Weapon_L"
    BACKPACK = "Socket_Backpack"
    WINGS = "Socket_Wings"
    ACCESSORY = "Socket_Accessory"
    HEADWEAR = "Socket_Headwear"


class AvatarAppearance(BaseModel):
    """Persistent modular appearance for a playable Mini Utopia Avatar.

    The rig stays fixed. Identity comes from swappable appearance modules.
    Existing Character records can omit this object because every field has
    a backward-compatible default.
    """

    schema_version: str = AVATAR_SCHEMA_VERSION
    customized: bool = False
    rig_family: str = AVATAR_RIG_FAMILY
    body_type: BodyType = BodyType.STANDARD

    species_head_id: str = "species_head_human_v1"

    surface_type: str = "skin"
    surface_color_hex: str = "#F2C7A5"

    eye_style_id: str = "eyes_round_soft_v1"
    eye_color_hex: str = "#7A5238"

    hair_style_id: str = "hair_none"
    hair_color_hex: str = "#5B4036"

    compatible_tags: list[str] = Field(
        default_factory=lambda: ["humanoid"]
    )


def avatar_socket_names() -> tuple[str, ...]:
    """Return the canonical runtime node names in stable order."""

    return tuple(socket.value for socket in AvatarSocket)
