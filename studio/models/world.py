from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio.models.location import LocationProfile


WORLD_SCHEMA_VERSION = "0.1"
BLUEPRINT_SCHEMA_VERSION = "0.4"
SCENE_PLAN_SCHEMA_VERSION = "0.1"


class GridSpec(BaseModel):
    width: int = Field(default=50, ge=10, le=1000)
    depth: int = Field(default=50, ge=10, le=1000)
    cell_size: float = Field(default=1.0, gt=0)
    chunk_width: int = Field(default=10, ge=1)
    chunk_depth: int = Field(default=10, ge=1)


class WorldPoint(BaseModel):
    x: float
    y: float = 0.0
    z: float


class SpawnPoint(WorldPoint):
    facing_degrees: float = 0.0


class LandmarkSpec(BaseModel):
    landmark_id: str
    name: str
    position: WorldPoint
    kind: str = ""
    asset_id: str | None = None
    required_for_concept_match: bool = True


class PortalSpec(BaseModel):
    position: WorldPoint
    facing_degrees: float = 0.0
    form: str = ""
    destination_hint: str = ""


class CameraPoint(BaseModel):
    camera_id: str
    position: WorldPoint
    look_at: WorldPoint
    lens_mm: float = Field(default=35.0, gt=0)
    role: Literal[
        "establishing",
        "follow",
        "landmark",
        "orbit",
        "portal_reveal",
        "ending",
        "custom",
    ] = "custom"


class TourStep(BaseModel):
    camera_id: str
    duration_seconds: float = Field(default=4.0, gt=0)
    movement: Literal["cut", "dolly", "orbit", "fly", "follow"] = "cut"


class TourRoute(BaseModel):
    name: str = "World Tour"
    steps: list[TourStep] = Field(default_factory=list)
    character_route_point_ids: list[str] = Field(default_factory=list)


class PathSpec(BaseModel):
    path_id: str
    name: str = ""
    points: list[WorldPoint] = Field(default_factory=list)
    width_cells: float = Field(default=2.0, gt=0)
    walkable: bool = True


class ZoneSpec(BaseModel):
    zone_id: str
    name: str = ""
    kind: Literal["walkable", "blocked", "water", "landmark", "portal", "spawn"] = "walkable"
    min_x: float
    max_x: float
    min_z: float
    max_z: float


class ChunkSpec(BaseModel):
    chunk_x: int
    chunk_z: int
    generated: bool = False
    biome: str = ""
    theme_hint: str = ""
    expansion_locked: bool = False


class ExpansionEdge(BaseModel):
    edge: Literal["north", "south", "east", "west"]
    open_for_growth: bool = True
    continuation_hint: str = ""


class WorldLayoutElement(BaseModel):
    """Executable semantic placement compiled from Scene Plan or legacy visual evidence."""

    element_id: str
    name: str
    kind: Literal[
        "portal",
        "landmark",
        "structure",
        "water",
        "terrain",
        "bridge",
        "decoration",
    ] = "landmark"
    position: WorldPoint
    width: float = Field(default=6.0, gt=0)
    depth: float = Field(default=6.0, gt=0)
    height: float = Field(default=4.0, gt=0)
    source_evidence: list[str] = Field(default_factory=list)


class WorldVisualAnchor(BaseModel):
    """Creator-approved concept direction.

    The concept image is a visual anchor for interpretation, not executable world data.
    """

    concept_image_roles: list[str] = Field(default_factory=list)
    concept_path: str = ""
    concept_direction: str = ""
    extraction_method: str = ""
    concept_summary: str = ""
    must_preserve: list[str] = Field(default_factory=list)
    flexible_details: list[str] = Field(default_factory=list)
    palette_hexes: list[str] = Field(default_factory=list)
    composition_notes: list[str] = Field(default_factory=list)
    spatial_relations: list[str] = Field(default_factory=list)


class WorldVisualAnalysis(BaseModel):
    """Visible evidence extracted from an approved World Concept image."""

    model_config = ConfigDict(extra="forbid")

    concept_summary: str
    must_preserve: list[str]
    flexible_details: list[str]
    palette_hexes: list[str]
    composition_notes: list[str]
    spatial_relations: list[str]


class WorldProfile(LocationProfile):
    """Creator-facing Mini World profile.

    World-specific identity inherits the Universe-level Style Canon instead of
    defining a competing character/world style system.
    """

    schema_version: str = WORLD_SCHEMA_VERSION
    source_description: str = ""
    creator_extra_details: str = ""

    world_name: str = ""
    world_type: str = ""
    reality_mode: str = ""
    story_function: str = ""

    terrain: list[str] = Field(default_factory=list)
    season: str = ""
    weather: str = ""
    time_of_day: str = ""
    water_features: list[str] = Field(default_factory=list)
    landscape_elements: list[str] = Field(default_factory=list)

    mood: list[str] = Field(default_factory=list)
    landmark_ideas: list[str] = Field(default_factory=list)
    portal_form: str = ""
    portal_placement_idea: str = ""
    traversability_notes: str = ""
    hazards: list[str] = Field(default_factory=list)
    surprise_elements: list[str] = Field(default_factory=list)

    # Theme colors can vary by world, but must obey the Universe Style Canon.
    theme_color_hexes: list[str] = Field(default_factory=list)

    playable: bool = True


class WorldSceneElement(BaseModel):
    """Semantic object in a creator world before runtime coordinates are assigned."""

    scene_id: str
    name: str
    kind: Literal[
        "portal",
        "landmark",
        "structure",
        "water",
        "terrain",
        "bridge",
        "decoration",
    ]
    source: Literal[
        "creator_required",
        "utopia_enrichment",
        "custom_selection",
        "system_required",
    ]
    required: bool = True
    placement_hint: str = ""
    relation_hints: list[str] = Field(default_factory=list)
    photo_opportunity: bool = False
    notes: str = ""


class WorldScenePlan(BaseModel):
    """Shared semantic contract between Prompt/Custom creation and Blueprint."""

    schema_version: str = SCENE_PLAN_SCHEMA_VERSION
    source_mode: Literal["prompt", "custom"]
    summary: str
    route_intent: str
    elements: list[WorldSceneElement] = Field(min_length=1, max_length=16)
    spatial_relations: list[str] = Field(default_factory=list, max_length=20)
    exploration_order: list[str] = Field(default_factory=list, max_length=16)
    photo_spot_ids: list[str] = Field(default_factory=list, max_length=8)
    enrichment_notes: list[str] = Field(default_factory=list, max_length=6)


class WorldPromptInterpretation(BaseModel):
    """GPT interpretation of one creator Prompt, including controlled Utopia enrichment."""

    world_name: str
    world_type: str
    reality_mode: str
    story_function: str
    terrain: list[str]
    season: str
    weather: str
    time_of_day: str
    architecture: str
    mood: list[str]
    portal_form: str
    theme_color_hexes: list[str]
    scene_plan: WorldScenePlan

    def to_profile(self, *, source_description: str) -> WorldProfile:
        scene = self.scene_plan
        waters = [item.name for item in scene.elements if item.kind == "water"]
        landmarks = [
            item.name
            for item in scene.elements
            if item.kind in {"landmark", "structure", "bridge"}
            and item.source != "utopia_enrichment"
        ]
        landscape = [
            item.name
            for item in scene.elements
            if item.kind in {"terrain", "decoration"}
        ]
        surprises = [
            item.name
            for item in scene.elements
            if item.source == "utopia_enrichment"
        ]
        return WorldProfile(
            source_description=source_description,
            world_name=self.world_name,
            world_type=self.world_type,
            reality_mode=self.reality_mode,
            story_function=self.story_function,
            terrain=list(self.terrain),
            season=self.season,
            weather=self.weather,
            time_of_day=self.time_of_day,
            architecture=self.architecture,
            water_features=waters,
            landscape_elements=landscape,
            mood=list(self.mood),
            landmark_ideas=landmarks,
            portal_form=self.portal_form,
            portal_placement_idea="Follow the Scene Plan spatial relations.",
            traversability_notes=scene.route_intent,
            surprise_elements=surprises,
            theme_color_hexes=list(self.theme_color_hexes),
            playable=True,
        )


class WorldBlueprint(BaseModel):
    """Saved source of truth for an expandable playable Mini World."""

    schema_version: str = BLUEPRINT_SCHEMA_VERSION
    location_asset_id: str | None = None
    style_asset_id: str | None = None

    grid: GridSpec = Field(default_factory=GridSpec)
    spawn: SpawnPoint = Field(default_factory=lambda: SpawnPoint(x=25, y=0, z=25))
    chunks: list[ChunkSpec] = Field(default_factory=list)
    landmarks: list[LandmarkSpec] = Field(default_factory=list)
    portal: PortalSpec | None = None
    paths: list[PathSpec] = Field(default_factory=list)
    zones: list[ZoneSpec] = Field(default_factory=list)

    walkable_zone_ids: list[str] = Field(default_factory=list)
    blocked_zone_ids: list[str] = Field(default_factory=list)

    visual_anchor: WorldVisualAnchor = Field(default_factory=WorldVisualAnchor)
    layout_elements: list[WorldLayoutElement] = Field(default_factory=list)
    camera_points: list[CameraPoint] = Field(default_factory=list)
    director_tours: list[TourRoute] = Field(default_factory=list)
    expansion_edges: list[ExpansionEdge] = Field(
        default_factory=lambda: [
            ExpansionEdge(edge="north"),
            ExpansionEdge(edge="south"),
            ExpansionEdge(edge="east"),
            ExpansionEdge(edge="west"),
        ]
    )

    def expected_chunk_count(self) -> int:
        return (self.grid.width // self.grid.chunk_width) * (
            self.grid.depth // self.grid.chunk_depth
        )
