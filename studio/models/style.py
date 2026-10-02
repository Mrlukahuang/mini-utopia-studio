from __future__ import annotations

from pydantic import BaseModel, Field


STYLE_SCHEMA_VERSION = "1.1"


class MacaronPaletteProfile(BaseModel):
    """Color behavior shared by Mini Utopia Canon visuals."""

    enabled_families: list[str] = Field(default_factory=list)
    saturation: str = "low-to-medium"
    lightness: str = "high"
    gradients: str = "soft"
    material_response: str = "creamy and dreamy"
    avoid: list[str] = Field(default_factory=list)


class StyleProfile(BaseModel):
    """Reusable STYLE asset profile.

    A StyleProfile describes visual language, not story content.
    World Style Packs can inherit from a parent style and override only
    world-specific expression while preserving the Mini Utopia base DNA.
    """

    schema_version: str = STYLE_SCHEMA_VERSION
    parent_style_asset_id: str | None = None

    visual_dna_pillars: list[str] = Field(default_factory=list)
    medium: str = ""
    shape_language: str = ""
    character_scale_language: str = ""
    face_language: str = ""
    gameplay_silhouette: str = ""
    material_language: str = ""
    lighting: str = ""
    camera_language: str = ""
    palette_notes: str = ""
    macaron_palette: MacaronPaletteProfile = Field(default_factory=MacaronPaletteProfile)

    locked_rules: list[str] = Field(default_factory=list)
    flexible_expression: list[str] = Field(default_factory=list)
    positive_rules: list[str] = Field(default_factory=list)
    negative_rules: list[str] = Field(default_factory=list)

    portal_language: str = ""
    composition_guide: str = "70% Mini Utopia DNA / 20% World identity / 10% Scene surprise"

    reference_asset_ids: list[str] = Field(default_factory=list)
