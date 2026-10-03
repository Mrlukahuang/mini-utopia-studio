from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from studio.models.render import (
    ObjectAppearanceSpec,
    RenderVec3,
    ShapePartSpec,
    WorldAppearancePlan,
    WorldRenderSpec,
)
from studio.models.world import (
    WorldBlueprint,
    WorldLayoutElement,
    WorldPoint,
    WorldProfile,
    WorldSceneElement,
    WorldScenePlan,
)
from studio.providers.base import ImageAnalysisProvider, ImageGenerationProvider, StructuredTextProvider
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.runtime.three_world import build_world_runtime_html
from studio.services.asset_service import AssetService
from studio.services.style_service import StyleService
from studio.services.world_appearance_service import (
    WorldAppearancePlanningError,
    WorldAppearanceService,
)
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_concept_service import WorldConceptService
from studio.services.world_geometry_compiler_service import WorldGeometryCompilerService
from studio.storage.local import LocalObjectStorage
class FakeWorldImageProvider(ImageGenerationProvider):
    def __init__(self):
        self.calls = []

    def generate(
        self,
        *,
        prompt: str,
        size: str = "1536x1024",
        quality: str = "medium",
    ) -> bytes:
        self.calls.append({"prompt": prompt, "size": size, "quality": quality})
        return b"fake-world-image"


class FakeStructuredAppearanceProvider(StructuredTextProvider):
    def __init__(self, payload, *, object_payload=None):
        self.payload = payload
        self.object_payload = object_payload
        self.calls = []

    def generate_structured(self, *, system: str, user: str, schema: Type[BaseModel]):
        self.calls.append({"system": system, "user": user, "schema": schema})
        payload = self.payload
        if schema is ObjectAppearanceSpec:
            payload = self.object_payload or self.payload["objects"][0]
        return schema.model_validate(payload)


class FakeVisionAppearanceProvider(ImageAnalysisProvider):
    def __init__(self, payload, *, object_payload=None):
        self.payload = payload
        self.object_payload = object_payload
        self.calls = []

    def analyze_structured(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        schema: Type[BaseModel],
    ):
        self.calls.append(
            {
                "image_bytes": image_bytes,
                "mime_type": mime_type,
                "prompt": prompt,
                "schema": schema,
            }
        )
        payload = self.payload
        if schema is ObjectAppearanceSpec:
            payload = self.object_payload or self.payload["objects"][0]
        return schema.model_validate(payload)


def _profile() -> WorldProfile:
    return WorldProfile(
        world_name="Cloud Whale Station",
        source_description=(
            "A gentle whale floats in the sky carrying a walkable flower station "
            "and a moon portal on its back."
        ),
        world_type="Sky Station",
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3", "#BDE3F7", "#FFF4D7"],
        portal_form="Moon Portal",
    )


def _blueprint() -> WorldBlueprint:
    return WorldBlueprint(
        location_asset_id="LOC_RENDER",
        layout_elements=[
            WorldLayoutElement(
                element_id="SCENE_WHALE",
                name="Gentle Sky Whale",
                kind="landmark",
                semantic_key="sky_whale",
                spatial_mode="aerial",
                elevation="high",
                geometry_role="organic",
                traversability="scenic",
                position=WorldPoint(x=40, y=16, z=40),
                width=18,
                depth=9,
                height=8,
            ),
            WorldLayoutElement(
                element_id="SCENE_STATION",
                name="Whale Back Garden",
                kind="terrain",
                semantic_key="whale_back_garden",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="platform",
                traversability="walkable",
                position=WorldPoint(x=40, y=24, z=40),
                width=11,
                depth=8,
                height=2,
            ),
        ],
    )


def _appearance_payload():
    return {
        "schema_version": "0.1",
        "world_style_summary": "One coherent Mini Utopia soft-voxel toy world.",
        "objects": [
            {
                "element_id": "SCENE_WHALE",
                "name": "GPT tried another name",
                "geometry_strategy": "procedural",
                "silhouette_family": "organic_creature",
                "silhouette_notes": "Long friendly body with tail and side fins.",
                "main_body": {
                    "part_id": "body",
                    "role": "main_body",
                    "primitive": "ellipsoid",
                    "parent_part_id": "",
                    "local_position": {"x": 0, "y": 0, "z": 0},
                    "rotation_degrees": {"x": 0, "y": 0, "z": 0},
                    "relative_scale": {"x": 1, "y": .72, "z": .82},
                    "palette_role": "sky",
                    "material_role": "toy_soft",
                    "surface_detail": "soft voxel facets",
                },
                "parts": [
                    {
                        "part_id": "tail",
                        "role": "rear_tail",
                        "primitive": "cone",
                        "parent_part_id": "",
                        "local_position": {"x": -.58, "y": 0, "z": 0},
                        "rotation_degrees": {"x": 0, "y": 0, "z": 90},
                        "relative_scale": {"x": .32, "y": .22, "z": .42},
                        "palette_role": "sky",
                        "material_role": "toy_soft",
                        "surface_detail": "",
                    },
                    {
                        "part_id": "left_fin",
                        "role": "side_fin",
                        "primitive": "ellipsoid",
                        "parent_part_id": "",
                        "local_position": {"x": 0, "y": -.1, "z": .55},
                        "rotation_degrees": {"x": 0, "y": 25, "z": 0},
                        "relative_scale": {"x": .35, "y": .10, "z": .30},
                        "palette_role": "secondary",
                        "material_role": "toy_soft",
                        "surface_detail": "",
                    },
                ],
                "sockets": [
                    {
                        "socket_id": "back_top",
                        "role": "walkable_surface",
                        "local_position": {"x": 0, "y": .5, "z": 0},
                        "local_direction": {"x": 0, "y": 1, "z": 0},
                    }
                ],
                "detail_density": "medium",
                "edge_profile": "soft_round",
                "symmetry": "bilateral",
                "preview_bbox": {"x": .35, "y": .1, "width": .55, "height": .52},
                "preview_evidence": "Large sky-blue whale visible in upper-right.",
                "creator_evidence": "gentle whale carrying a station",
            }
        ],
    }


def test_appearance_planner_keeps_blueprint_ids_and_fills_missing_objects():
    provider = FakeStructuredAppearanceProvider(_appearance_payload())
    service = WorldAppearanceService(structured_provider=provider)

    plan = service.plan_from_blueprint(
        profile=_profile(),
        blueprint=_blueprint(),
        style_profile={
            "visual_dna_pillars": ["Voxel", "Toy-like"],
            "world_geometry_language": "rounded block-built",
            "runtime_material_rule": "matte collectible-toy",
            "macaron_palette": {"enabled_families": ["mint", "lavender"]},
        },
    )

    assert [item.element_id for item in plan.objects] == [
        "SCENE_WHALE",
        "SCENE_STATION",
    ]
    assert plan.objects[0].name == "Gentle Sky Whale"
    assert plan.objects[0].main_body.primitive == "ellipsoid"
    assert plan.objects[1].name == "Whale Back Garden"
    assert "MINI UTOPIA STYLE CONSTITUTION" in provider.calls[0]["system"]
    assert "Never move" not in provider.calls[0]["user"]
    assert '"element_id": "SCENE_WHALE"' in provider.calls[0]["user"]


def test_preview_vision_refines_appearance_without_changing_blueprint_identity():
    vision = FakeVisionAppearanceProvider(_appearance_payload())
    service = WorldAppearanceService(image_analysis_provider=vision)
    blueprint = _blueprint()
    before = blueprint.model_dump(mode="json")
    base = service.plan_from_blueprint(
        profile=_profile(),
        blueprint=blueprint,
        style_profile={},
    )

    refined = service.refine_from_preview(
        profile=_profile(),
        blueprint=blueprint,
        style_profile={},
        base_plan=base,
        image_bytes=b"preview",
    )

    assert blueprint.model_dump(mode="json") == before
    assert refined.objects[0].element_id == "SCENE_WHALE"
    assert refined.objects[0].parts[0].part_id == "tail"
    assert refined.objects[1].element_id == "SCENE_STATION"
    assert "Never move, resize, delete, reorder, or reconnect" in vision.calls[0]["prompt"]


def test_geometry_compiler_preserves_blueprint_transform_and_resolves_style_materials():
    appearance = WorldAppearancePlan.model_validate(_appearance_payload())
    # Normalization/fallback for the station is handled by WorldAppearanceService.
    appearance = WorldAppearanceService()._normalize(
        proposed=appearance,
        blueprint=_blueprint(),
        fallback=WorldAppearanceService().plan_from_blueprint(
            profile=_profile(),
            blueprint=_blueprint(),
            style_profile={},
        ),
    )
    render = WorldGeometryCompilerService().compile(
        profile=_profile(),
        blueprint=_blueprint(),
        appearance=appearance,
        style_profile={},
    )

    whale = next(item for item in render.objects if item.element_id == "SCENE_WHALE")
    assert whale.transform.position == WorldPoint(x=40, y=16, z=40)
    assert whale.semantic_key == "sky_whale"
    assert whale.spatial_mode == "aerial"
    assert len(whale.nodes) == 3
    body = next(node for node in whale.nodes if node.node_id.endswith(":body"))
    assert body.geometry.primitive == "ellipsoid"
    assert body.geometry.primitive_size.x == 18
    assert body.geometry.primitive_size.y == 8 * .72
    assert any(material.color_hex == "#BDE3F7" for material in render.materials)
    assert all(material.metalness == 0 for material in render.materials)


def test_three_runtime_prefers_render_spec_but_keeps_blueprint_fallback():
    appearance = WorldAppearanceService().plan_from_blueprint(
        profile=_profile(),
        blueprint=_blueprint(),
        style_profile={},
    )
    render = WorldGeometryCompilerService().compile(
        profile=_profile(),
        blueprint=_blueprint(),
        appearance=appearance,
        style_profile={},
    )

    html = build_world_runtime_html(
        world_name="Cloud Whale Station",
        profile=_profile(),
        blueprint=_blueprint(),
        render_spec=render,
    )

    assert '"renderSpec": {' in html
    assert "function addCompiledRenderObject" in html
    assert "function bufferGeometryFromSpec" in html
    assert "compiledElementIds" in html
    assert "renderSpec?.environment?.lights?.length" in html
    assert "SCENE_WHALE" in html


def test_world_pipeline_persists_initial_render_spec_and_preview_refinement(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    assets = AssetService(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    profile = _profile()
    world = assets.create_world(
        name=profile.world_name,
        description=profile.source_description,
        profile=profile,
    )

    structured = FakeStructuredAppearanceProvider(_appearance_payload())
    vision = FakeVisionAppearanceProvider(_appearance_payload())
    appearance_service = WorldAppearanceService(
        structured_provider=structured,
        image_analysis_provider=vision,
    )
    service = WorldConceptService(
        repo,
        storage,
        WorldConceptPromptService(),
        WorldBlueprintService(),
        image_provider=FakeWorldImageProvider(),
        appearance_service=appearance_service,
        geometry_compiler=WorldGeometryCompilerService(),
    )
    scene_plan = WorldScenePlan(
        source_mode="prompt",
        summary="Sky whale station",
        route_intent="Climb to the station and discover the Portal.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_WHALE",
                name="Gentle Sky Whale",
                semantic_key="sky_whale",
                kind="landmark",
                source="creator_required",
                spatial_mode="aerial",
                elevation="high",
                geometry_role="organic",
                traversability="scenic",
            ),
            WorldSceneElement(
                scene_id="SCENE_STATION",
                name="Whale Back Garden",
                semantic_key="whale_back_garden",
                kind="terrain",
                source="creator_required",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="platform",
                traversability="walkable",
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Moon Portal",
                semantic_key="moon_portal",
                kind="portal",
                source="creator_required",
                geometry_role="arch",
                traversability="walkable",
            ),
        ],
        exploration_order=["SCENE_STATION", "SCENE_PORTAL"],
    )

    service.plan_blueprint(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        scene_plan=scene_plan,
    )
    planned = repo.get_asset(world.asset_id)
    assert planned is not None
    assert planned.metadata["world_render_spec"]["objects"]
    assert planned.metadata["world_appearance_source"] == "blueprint+creator_prompt"

    progress_events: list[tuple[str, str, float]] = []
    service.render_blueprint_preview(
        location_asset_id=world.asset_id,
        style_asset_id=style.asset_id,
        progress_callback=lambda stage, message, progress: progress_events.append(
            (stage, message, progress)
        ),
    )
    rendered = repo.get_asset(world.asset_id)
    assert rendered is not None
    assert rendered.metadata["world_appearance_source"] == "blueprint+preview_vision"
    assert rendered.metadata["world_render_schema_version"] == "0.1"
    appearance_diag = rendered.metadata["world_appearance_diagnostics"]
    whale_diag = next(
        item
        for item in appearance_diag["objects"]
        if item["element_id"] == "SCENE_WHALE"
    )
    assert whale_diag["part_count"] >= 2
    assert whale_diag["weak_hero"] is False
    render_diag = rendered.metadata["world_render_diagnostics"]
    whale_render = next(
        item
        for item in render_diag["objects"]
        if item["element_id"] == "SCENE_WHALE"
    )
    assert whale_render["node_count"] >= 3
    assert "OBJECT APPEARANCE DIRECTION" in rendered.metadata["world_preview_last_prompt"]
    assert "SCENE_WHALE" in rendered.metadata["world_preview_last_prompt"]
    assert vision.calls

    stages = [stage for stage, _, _ in progress_events]
    assert stages == [
        "blueprint",
        "appearance",
        "appearance_ready",
        "art_direction",
        "preview",
        "preview_ready",
        "appearance",
        "vision",
        "geometry",
        "persist",
        "ready",
    ]
    progress_values = [progress for _, _, progress in progress_events]
    assert progress_values == sorted(progress_values)
    assert progress_values[-1] == 1.0
    assert "Gentle Sky Whale" in progress_events[0][1]
    assert any("Three.js RenderSpec" in message for _, message, _ in progress_events)


class FailingStructuredAppearanceProvider(StructuredTextProvider):
    def generate_structured(self, *, system: str, user: str, schema: Type[BaseModel]):
        raise RuntimeError("provider exploded")


def test_strict_appearance_does_not_silently_fall_back_on_provider_failure():
    service = WorldAppearanceService(
        structured_provider=FailingStructuredAppearanceProvider()
    )

    with pytest.raises(WorldAppearancePlanningError, match="AppearancePlan generation failed"):
        service.plan_from_blueprint(
            profile=_profile(),
            blueprint=_blueprint(),
            style_profile={},
            strict_provider=True,
        )


def test_non_strict_appearance_still_keeps_backward_compatible_fallback():
    service = WorldAppearanceService(
        structured_provider=FailingStructuredAppearanceProvider()
    )

    plan = service.plan_from_blueprint(
        profile=_profile(),
        blueprint=_blueprint(),
        style_profile={},
    )

    whale = next(item for item in plan.objects if item.element_id == "SCENE_WHALE")
    assert whale.main_body.primitive == "ellipsoid"
    assert whale.parts == []


def test_weak_organic_hero_gets_focused_shape_repair():
    weak = _appearance_payload()
    weak["objects"][0]["parts"] = []
    provider = FakeStructuredAppearanceProvider(
        weak,
        object_payload=_appearance_payload()["objects"][0],
    )
    service = WorldAppearanceService(structured_provider=provider)

    plan = service.plan_from_blueprint(
        profile=_profile(),
        blueprint=_blueprint(),
        style_profile={},
        strict_provider=True,
        repair_weak_heroes=True,
    )

    whale = next(item for item in plan.objects if item.element_id == "SCENE_WHALE")
    assert len(whale.parts) == 2
    assert [part.role for part in whale.parts] == ["rear_tail", "side_fin"]
    assert len(provider.calls) == 2
    assert provider.calls[1]["schema"] is ObjectAppearanceSpec
    assert "major organic Hero object" in provider.calls[1]["user"]


def test_strict_hero_repair_rejects_body_only_result():
    weak = _appearance_payload()
    weak["objects"][0]["parts"] = []
    provider = FakeStructuredAppearanceProvider(
        weak,
        object_payload=weak["objects"][0],
    )
    service = WorldAppearanceService(structured_provider=provider)

    with pytest.raises(WorldAppearancePlanningError, match="remained too weak"):
        service.plan_from_blueprint(
            profile=_profile(),
            blueprint=_blueprint(),
            style_profile={},
            strict_provider=True,
            repair_weak_heroes=True,
        )
