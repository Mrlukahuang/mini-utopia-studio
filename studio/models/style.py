from pydantic import BaseModel, Field


class StyleProfile(BaseModel):
    medium: str = ""
    shape_language: str = ""
    material_language: str = ""
    lighting: str = ""
    camera_language: str = ""
    palette_notes: str = ""
    positive_rules: list[str] = Field(default_factory=list)
    negative_rules: list[str] = Field(default_factory=list)
