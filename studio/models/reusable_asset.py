from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReusableAssetCategory = Literal[
    "tree",
    "plant",
    "grass",
    "rock",
    "mushroom",
    "cloud",
    "architecture",
    "bridge",
    "portal",
    "prop",
    "vehicle",
    "wearable",
    "hero",
    "other",
]

ReusableAssetOriginKind = Literal[
    "cc0_library",
    "generated",
    "manual",
    "derived",
]

ReusableAssetStyleStatus = Literal[
    "raw",
    "normalized",
    "approved",
]


class ReusableAssetSourceSpec(BaseModel):
    """Where a reusable GLB came from and under what terms."""

    origin_kind: ReusableAssetOriginKind
    source_name: str
    source_url: str = ""
    license_id: str = "UNKNOWN"
    attribution_required: bool = False
    generator_model: str = ""


class ReusableAssetNormalizationSpec(BaseModel):
    """Canonical transform/material expectations before an asset joins a World."""

    up_axis: Literal["y", "z"] = "y"
    forward_axis: Literal["x", "-x", "z", "-z"] = "z"
    ground_aligned: bool = True
    centered_xz: bool = True
    meters_per_unit: float = Field(default=1.0, gt=0.0)
    base_uniform_scale: float = Field(default=1.0, gt=0.0)
    material_profile: Literal[
        "source",
        "mini_utopia_toy_matte",
        "mini_utopia_toy_soft",
    ] = "source"


class ReusableAssetVariantPolicy(BaseModel):
    """What Mini Utopia may change without regenerating the source asset."""

    allow_uniform_scale: bool = True
    allow_palette_override: bool = True
    allow_material_override: bool = True
    allow_texture_swap: bool = False
    allow_geometry_edit: bool = False


class ReusableAssetVariantOverrides(BaseModel):
    """Non-destructive derived-variant instructions.

    The base GLB bytes remain immutable. Runtime/normalization code may apply
    these overrides when the asset is instantiated.
    """

    palette_hex_by_role: dict[str, str] = Field(default_factory=dict)
    roughness: float | None = Field(default=None, ge=0.0, le=1.0)
    metalness: float | None = Field(default=None, ge=0.0, le=1.0)
    uniform_scale: float = Field(default=1.0, gt=0.0)
    texture_replacements: dict[str, str] = Field(default_factory=dict)


class ReusableGLBSpec(BaseModel):
    """Typed metadata for one reusable Mini Utopia GLB asset."""

    schema_version: str = "0.1"
    category: ReusableAssetCategory
    semantic_keys: list[str] = Field(default_factory=list, max_length=32)
    storage_path: str
    sha256: str
    byte_size: int = Field(ge=0)
    source: ReusableAssetSourceSpec
    source_fingerprint: str = ""
    style_status: ReusableAssetStyleStatus = "raw"
    normalization: ReusableAssetNormalizationSpec = Field(
        default_factory=ReusableAssetNormalizationSpec
    )
    variant_policy: ReusableAssetVariantPolicy = Field(
        default_factory=ReusableAssetVariantPolicy
    )
    parent_asset_id: str = ""
    variant_overrides: ReusableAssetVariantOverrides = Field(
        default_factory=ReusableAssetVariantOverrides
    )


class ReusableAssetPackEntry(BaseModel):
    """One normalized GLB entry inside a portable Mini Utopia asset pack."""

    asset_key: str
    display_name: str
    category: ReusableAssetCategory
    semantic_keys: list[str] = Field(default_factory=list, max_length=32)
    source_pack: str = ""
    source_entry: str = ""
    source_name: str
    source_url: str = ""
    license_id: str = "UNKNOWN"
    attribution_required: bool = False
    glb_path: str
    sha256: str
    byte_size: int = Field(ge=0)
    style_status: ReusableAssetStyleStatus = "raw"
    normalization: ReusableAssetNormalizationSpec = Field(
        default_factory=ReusableAssetNormalizationSpec
    )
    variant_policy: ReusableAssetVariantPolicy = Field(
        default_factory=ReusableAssetVariantPolicy
    )
    tags: list[str] = Field(default_factory=list, max_length=32)


class ReusableAssetPackManifest(BaseModel):
    """Manifest for an offline-normalized reusable GLB pack."""

    schema_version: str = "1.0"
    name: str
    style_target: str = "Mini Utopia Visual DNA v1"
    assets: list[ReusableAssetPackEntry] = Field(default_factory=list, max_length=500)
