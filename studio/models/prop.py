from pydantic import BaseModel, Field


class PropProfile(BaseModel):
    category: str = ""
    appearance: str = ""
    function: str = ""
    scale_notes: str = ""
    immutable_features: list[str] = Field(default_factory=list)
