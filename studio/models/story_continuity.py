from __future__ import annotations

from pydantic import BaseModel, Field


class ContinuityEquipmentItem(BaseModel):
    item_instance_id: str
    display_name: str
    slot: str
    rarity: str
    hp: int = 0
    atk: int = 0
    defense: int = 0


class ContinuityCharacterState(BaseModel):
    asset_id: str
    display_name: str
    body_type: str
    species_head_id: str
    final_hp: int
    final_atk: int
    final_defense: int
    equipped: list[ContinuityEquipmentItem] = Field(default_factory=list)


class ContinuityBabyState(BaseModel):
    baby_id: str
    display_name: str
    species_id: str
    level: int
    xp: int
    bond: int


class ContinuityOwnedItem(BaseModel):
    item_instance_id: str
    display_name: str
    slot: str
    rarity: str
    favorite: bool = False


class ContinuityWorldState(BaseModel):
    asset_id: str
    display_name: str
    world_type: str = ""
    mood: list[str] = Field(default_factory=list)
    landmarks: list[str] = Field(default_factory=list)
    portal_form: str = ""
    gameplay_modes: list[str] = Field(default_factory=list)
    creative_decoration_count: int = 0


class ContinuityStoryState(BaseModel):
    story_id: str
    title: str
    premise: str
    hook: str = ""
    discovery: str = ""
    conflict: str = ""
    adventure: str = ""
    twist: str = ""
    ending: str = ""


class StoryContinuityContext(BaseModel):
    character_states: list[ContinuityCharacterState] = Field(default_factory=list)
    active_baby: ContinuityBabyState | None = None
    important_owned_items: list[ContinuityOwnedItem] = Field(default_factory=list)
    world: ContinuityWorldState | None = None
    prior_canon_stories: list[ContinuityStoryState] = Field(default_factory=list)

    @property
    def has_context(self) -> bool:
        return bool(
            self.character_states
            or self.active_baby
            or self.important_owned_items
            or self.world
            or self.prior_canon_stories
        )
