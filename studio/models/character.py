from pydantic import BaseModel, Field


class CharacterProfile(BaseModel):
    species: str = ""
    body: str = ""
    face: str = ""
    clothing: str = ""
    personality: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    habits: list[str] = Field(default_factory=list)
    color_notes: str = ""
    immutable_features: list[str] = Field(default_factory=list)
