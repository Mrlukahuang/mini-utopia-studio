from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ReferenceCharacterConfig(BaseModel):
    """Studio-level configuration for child-friendly relative comparisons.

    The referenced characters are normal reusable Character Assets. This model
    only stores their CHAR_IDs and scale factors; it never duplicates the
    characters themselves.
    """

    character_asset_ids: list[str] = Field(min_length=2, max_length=2)
    minimum_height_factor: float = Field(default=0.5, gt=0)
    maximum_height_factor: float = Field(default=2.0, gt=0)

    @model_validator(mode="after")
    def validate_distinct_character_ids(self):
        if len(set(self.character_asset_ids)) != 2:
            raise ValueError("Reference Characters must be two different CHAR_IDs.")
        return self

    def height_bounds(self, heights_cm: list[float]) -> tuple[float, float]:
        """Compute the visual ruler bounds from the two reference heights."""

        if len(heights_cm) != 2:
            raise ValueError("Exactly two reference heights are required.")
        if any(height <= 0 for height in heights_cm):
            raise ValueError("Reference heights must be positive.")

        shorter = min(heights_cm)
        taller = max(heights_cm)
        return (
            shorter * self.minimum_height_factor,
            taller * self.maximum_height_factor,
        )
