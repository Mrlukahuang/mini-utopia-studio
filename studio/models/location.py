from pydantic import BaseModel, Field


class LocationProfile(BaseModel):
    environment: str = ""
    architecture: str = ""
    sky: str = ""
    lighting: str = ""
    physical_rules: list[str] = Field(default_factory=list)
    landmarks: list[str] = Field(default_factory=list)
    immutable_features: list[str] = Field(default_factory=list)
