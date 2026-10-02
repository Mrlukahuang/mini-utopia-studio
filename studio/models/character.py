from __future__ import annotations

from pydantic import BaseModel, Field


CHARACTER_SCHEMA_VERSION = "1.1"

# These fields are expected before a Character is considered creator-ready.
# The parser may leave them blank when the source description does not specify them;
# the Creator UI is responsible for asking the child to complete them.
CORE_REQUIRED_FIELDS = (
    "character_type",
    "age",
    "appearance",
    "personality_traits",
    "speaking_tone",
    "native_language",
    "english_level",
)


class EyeProfile(BaseModel):
    """Reusable structured eye description kept inside a Character in v1."""

    shape: str = ""
    color: str = ""
    color_hex: str = "#6B4F3A"
    size: str = ""
    special_features: list[str] = Field(default_factory=list)


class WearableLoadout(BaseModel):
    """References to reusable WEAR assets.

    Wearables are independent Assets; the Character stores only their IDs.
    """

    top_id: str | None = None
    bottom_id: str | None = None
    shoes_id: str | None = None
    hat_id: str | None = None
    accessory_ids: list[str] = Field(default_factory=list)


class CharacterProfile(BaseModel):
    """Character Profile v1.

    The Character's mutable name lives on Asset.display_name and is intentionally
    not duplicated here.

    Visibility groups:
    - Core: child-facing fields shown by default.
    - Detail: child-facing fields available for deeper editing.
    - Studio: production/continuity metadata maintained by the system.
    """

    # Studio / provenance
    schema_version: str = CHARACTER_SCHEMA_VERSION
    source_description: str = ""

    # Core / 核心
    character_type: str = ""
    character_type_description: str = ""
    age: str = ""
    appearance: str = ""
    eyes: EyeProfile = Field(default_factory=EyeProfile)
    hair_or_fur: str = ""
    hair_style: str = ""
    hair_or_fur_color: str = ""
    hair_or_fur_color_hex: str = "#F4E9D8"
    body_build: str = ""
    height: str = ""
    height_cm: float | None = Field(default=None, gt=0, le=1000)
    favorite_colors: list[str] = Field(default_factory=list)
    favorite_color_hexes: list[str] = Field(default_factory=list)
    personality_traits: list[str] = Field(default_factory=list)
    speaking_tone: str = ""
    native_language: str = ""
    english_level: int | None = Field(default=None, ge=1, le=10)

    # Detail / 细节
    story_role: str = ""
    story_role_description: str = ""
    body_type: str = ""
    proportions: str = ""
    face: str = ""
    skin_fur_material: str = ""
    distinctive_features: list[str] = Field(default_factory=list)

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    fears: list[str] = Field(default_factory=list)
    habits: list[str] = Field(default_factory=list)
    likes: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)

    abilities: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    movement_style: str = ""

    wearables: WearableLoadout = Field(default_factory=WearableLoadout)
    starting_prop_ids: list[str] = Field(default_factory=list, max_length=2)

    # Studio / visual continuity
    visual_palette: list[str] = Field(default_factory=list)
    immutable_features: list[str] = Field(default_factory=list)
    flexible_features: list[str] = Field(default_factory=list)

    def missing_core_fields(self) -> list[str]:
        """Return creator-required fields that still need an explicit choice."""

        missing: list[str] = []
        for field_name in CORE_REQUIRED_FIELDS:
            value = getattr(self, field_name)
            if value is None or value == "" or value == []:
                missing.append(field_name)
        return missing
