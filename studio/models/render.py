from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from studio.models.world import WorldPoint


RENDER_SPEC_SCHEMA_VERSION = "0.2"


class RenderVec3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class RenderQuaternion(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


class PreviewBBox(BaseModel):
    """Normalized 0..1 preview-image region for future targeted refinement."""

    x: float = Field(default=0.0, ge=0.0, le=1.0)
    y: float = Field(default=0.0, ge=0.0, le=1.0)
    width: float = Field(default=1.0, ge=0.0, le=1.0)
    height: float = Field(default=1.0, ge=0.0, le=1.0)


PaletteRole = Literal[
    "primary",
    "secondary",
    "accent",
    "cream",
    "sky",
    "water",
    "foliage",
    "glow",
    "dark_accent",
]

MaterialRole = Literal[
    "toy_matte",
    "toy_soft",
    "translucent",
    "emissive",
    "water",
    "foliage",
    "glass_soft",
]

PrimitiveType = Literal[
    "box",
    "rounded_box",
    "sphere",
    "ellipsoid",
    "cylinder",
    "cone",
    "capsule",
    "hemisphere",
    "dome",
    "wedge",
    "tapered_box",
    "disc",
    "torus",
    "ring",
    "plane",
    "arch",
    "voxel_cluster",
]


class ShapePartSpec(BaseModel):
    """GPT-facing object-local shape grammar.

    relative_scale is the fraction of the authoritative Blueprint envelope
    occupied by the part on each axis. local_position is normalized from
    -1..1 across the envelope half-extents: 0 is the object center, -1/+1 are
    the negative/positive envelope faces before part-size clamping.

    parent_part_id is semantic attachment metadata in RenderSpec v0.2. It does
    not create an additional transform space; compiled mesh transforms remain
    object-local so GPT cannot accidentally accumulate parent transforms.
    """

    part_id: str
    role: str
    primitive: PrimitiveType
    parent_part_id: str = ""
    local_position: RenderVec3 = Field(default_factory=RenderVec3)
    rotation_degrees: RenderVec3 = Field(default_factory=RenderVec3)
    relative_scale: RenderVec3 = Field(
        default_factory=lambda: RenderVec3(x=1.0, y=1.0, z=1.0)
    )
    palette_role: PaletteRole = "primary"
    material_role: MaterialRole = "toy_matte"
    surface_detail: str = ""


class AttachmentSocketSpec(BaseModel):
    socket_id: str
    role: Literal[
        "support",
        "walkable_surface",
        "attachment",
        "portal_mount",
        "path_connection",
        "decoration_mount",
    ] = "attachment"
    local_position: RenderVec3 = Field(default_factory=RenderVec3)
    local_direction: RenderVec3 = Field(
        default_factory=lambda: RenderVec3(x=0.0, y=1.0, z=0.0)
    )


class ObjectAppearanceSpec(BaseModel):
    """Detailed visual description for exactly one authoritative Blueprint element."""

    element_id: str
    name: str
    geometry_strategy: Literal["procedural", "voxel", "glb", "hybrid"] = "procedural"
    silhouette_family: Literal[
        "organic_creature",
        "architecture",
        "terrain",
        "bridge",
        "portal",
        "vegetation",
        "water",
        "prop",
        "abstract",
    ] = "abstract"
    silhouette_notes: str = ""
    main_body: ShapePartSpec
    parts: list[ShapePartSpec] = Field(default_factory=list, max_length=24)
    sockets: list[AttachmentSocketSpec] = Field(default_factory=list, max_length=12)
    detail_density: Literal["low", "medium", "high"] = "medium"
    edge_profile: Literal["soft_round", "rounded_block", "chunky_bevel"] = "rounded_block"
    symmetry: Literal["none", "bilateral", "radial"] = "none"
    preview_bbox: PreviewBBox = Field(default_factory=PreviewBBox)
    preview_evidence: str = ""
    creator_evidence: str = ""


class WorldAppearancePlan(BaseModel):
    """GPT/vision output. Appearance only; Blueprint logic remains authoritative."""

    schema_version: str = RENDER_SPEC_SCHEMA_VERSION
    world_style_summary: str
    objects: list[ObjectAppearanceSpec] = Field(default_factory=list, max_length=32)


class ThreeBufferGeometrySpec(BaseModel):
    """Direct BufferGeometry payload for compiled voxel/custom meshes."""

    positions: list[float] = Field(default_factory=list)
    indices: list[int] = Field(default_factory=list)
    normals: list[float] = Field(default_factory=list)
    uvs: list[float] = Field(default_factory=list)
    colors: list[float] = Field(default_factory=list)


class ThreeGeometrySpec(BaseModel):
    source_type: Literal["primitive", "buffer", "glb"] = "primitive"
    primitive: PrimitiveType = "box"
    primitive_size: RenderVec3 = Field(
        default_factory=lambda: RenderVec3(x=1.0, y=1.0, z=1.0)
    )
    # Small generated meshes may be inline. Large voxel/custom geometry should
    # be stored as an external binary/GLB asset and referenced here.
    buffer: ThreeBufferGeometrySpec = Field(default_factory=ThreeBufferGeometrySpec)
    asset_path: str = ""
    asset_mime_type: str = ""
    asset_sha256: str = ""


class ThreeTextureSpec(BaseModel):
    texture_id: str
    usage: Literal[
        "map",
        "normal",
        "roughness",
        "metalness",
        "emissive",
        "alpha",
        "environment",
    ]
    asset_path: str
    mime_type: str = "image/png"
    color_space: Literal["srgb", "none"] = "srgb"
    wrap: Literal["clamp", "repeat", "mirror"] = "clamp"
    repeat_x: float = Field(default=1.0, gt=0)
    repeat_y: float = Field(default=1.0, gt=0)


class ThreeMaterialSpec(BaseModel):
    material_id: str
    model: Literal["standard", "toon"] = "standard"
    palette_role: PaletteRole = "primary"
    color_hex: str
    roughness: float = Field(default=0.72, ge=0.0, le=1.0)
    metalness: float = Field(default=0.0, ge=0.0, le=1.0)
    emissive_hex: str = "#000000"
    emissive_intensity: float = Field(default=0.0, ge=0.0, le=8.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    transparent: bool = False
    alpha_test: float = Field(default=0.0, ge=0.0, le=1.0)
    side: Literal["front", "back", "double"] = "front"
    vertex_colors: bool = False
    map_texture_id: str = ""
    normal_texture_id: str = ""
    roughness_texture_id: str = ""
    metalness_texture_id: str = ""
    emissive_texture_id: str = ""
    alpha_texture_id: str = ""


class ThreeMeshNodeSpec(BaseModel):
    node_id: str
    parent_node_id: str = ""
    geometry: ThreeGeometrySpec
    material_id: str
    local_position: RenderVec3 = Field(default_factory=RenderVec3)
    local_quaternion: RenderQuaternion = Field(default_factory=RenderQuaternion)
    local_scale: RenderVec3 = Field(
        default_factory=lambda: RenderVec3(x=1.0, y=1.0, z=1.0)
    )
    cast_shadow: bool = True
    receive_shadow: bool = True
    visible: bool = True
    render_order: int = 0


class ThreeObjectTransformSpec(BaseModel):
    position: WorldPoint
    quaternion: RenderQuaternion = Field(default_factory=RenderQuaternion)
    scale: RenderVec3 = Field(
        default_factory=lambda: RenderVec3(x=1.0, y=1.0, z=1.0)
    )


class ThreeObjectSpec(BaseModel):
    element_id: str
    name: str
    kind: str = ""
    semantic_key: str = ""
    spatial_mode: str = "grounded"
    traversability: str = "scenic"
    transform: ThreeObjectTransformSpec
    nodes: list[ThreeMeshNodeSpec] = Field(default_factory=list, max_length=32)
    visible: bool = True
    cast_shadow: bool = True
    receive_shadow: bool = True
    render_order: int = 0
    frustum_culled: bool = True
    layer: int = Field(default=0, ge=0, le=31)
    animation_clip_names: list[str] = Field(default_factory=list, max_length=16)
    source: Literal["appearance_spec", "deterministic_fallback"] = "appearance_spec"


class RenderCameraSpec(BaseModel):
    fov_degrees: float = Field(default=48.0, gt=1.0, lt=179.0)
    near: float = Field(default=0.1, gt=0.0)
    far: float = Field(default=300.0, gt=1.0)
    zoom: float = Field(default=1.0, gt=0.0)
    film_gauge_mm: float = Field(default=35.0, gt=0.0)


class RenderRendererSpec(BaseModel):
    antialias: bool = True
    pixel_ratio_cap: float = Field(default=2.0, gt=0.0, le=4.0)
    shadows_enabled: bool = True
    shadow_map_size: int = Field(default=2048, ge=256, le=8192)
    tone_mapping: Literal["aces", "linear", "none"] = "aces"
    exposure: float = Field(default=1.0, gt=0.0, le=4.0)


class RenderLightSpec(BaseModel):
    light_id: str
    kind: Literal["ambient", "hemisphere", "directional", "point"]
    color_hex: str = "#FFFFFF"
    intensity: float = Field(default=1.0, ge=0.0, le=50.0)
    position: RenderVec3 = Field(default_factory=RenderVec3)
    target: RenderVec3 = Field(default_factory=RenderVec3)
    cast_shadow: bool = False


class RenderEnvironmentSpec(BaseModel):
    background_hex: str = "#CFEAF6"
    fog_hex: str = "#DDEFF6"
    fog_near: float = 55.0
    fog_far: float = 140.0
    environment_intensity: float = Field(default=0.8, ge=0.0, le=4.0)
    lights: list[RenderLightSpec] = Field(default_factory=list, max_length=8)


class WorldRenderSpec(BaseModel):
    """Stable Three.js-facing render contract compiled from Blueprint + appearance."""

    schema_version: str = RENDER_SPEC_SCHEMA_VERSION
    location_asset_id: str | None = None
    blueprint_schema_version: str = ""
    appearance_schema_version: str = RENDER_SPEC_SCHEMA_VERSION
    textures: list[ThreeTextureSpec] = Field(default_factory=list, max_length=64)
    materials: list[ThreeMaterialSpec] = Field(default_factory=list, max_length=64)
    objects: list[ThreeObjectSpec] = Field(default_factory=list, max_length=32)
    camera: RenderCameraSpec = Field(default_factory=RenderCameraSpec)
    renderer: RenderRendererSpec = Field(default_factory=RenderRendererSpec)
    environment: RenderEnvironmentSpec = Field(default_factory=RenderEnvironmentSpec)
