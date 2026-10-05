from __future__ import annotations

import io
import struct

from PIL import Image

from studio.models.hero_composition import WorldHeroCompositionPlan
from studio.models.render import ObjectAppearanceSpec, ShapePartSpec, WorldAppearancePlan
from studio.models.world import (
    WorldBlueprint,
    WorldLayoutElement,
    WorldPoint,
    WorldProfile,
    WorldVisualAnchor,
)
from studio.providers.base import ImageGenerationProvider
from studio.providers.hero_asset import HeroAssetProvider, HeroAssetResult
from studio.services.world_geometry_compiler_service import WorldGeometryCompilerService
from studio.services.world_hero_asset_service import WorldHeroAssetService
from studio.storage.local import LocalObjectStorage


def _png() -> bytes:
    image = Image.new("RGBA", (640, 640), (165, 188, 210, 255))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _glb() -> bytes:
    return b"glTF" + struct.pack("<II", 2, 12)


class CaptureReferenceProvider(ImageGenerationProvider):
    def __init__(self):
        self.calls = []

    def generate(self, *, prompt: str, size: str = "1024x1536", quality: str = "medium") -> bytes:
        self.calls.append({"prompt": prompt, "size": size, "quality": quality})
        return _png()


class CaptureHeroProvider(HeroAssetProvider):
    cache_identity = "fake:pixal3d:cluster-v1"
    model = "pixal3d"

    def __init__(self, *, fail: bool = False):
        self.calls = []
        self.fail = fail

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("fake GPU failure")
        return HeroAssetResult(
            payload=_glb(),
            mime_type="model/gltf-binary",
            model="pixal3d",
            provider="huggingface_space",
            metadata={
                "zero_gpu_usage": {
                    "status": "ok",
                    "kind": "generation",
                    "gpu_seconds": 42.0,
                    "wall_seconds": 55.0,
                    "remaining_seconds": 900.0,
                    "base_seconds": 1200.0,
                }
            },
        )


def _blueprint() -> WorldBlueprint:
    return WorldBlueprint(
        location_asset_id="LOC_CLOUD_WHALE",
        visual_anchor=WorldVisualAnchor(
            concept_summary="A living sky whale that is also a magical station.",
            must_preserve=[
                "gentle whale silhouette",
                "flower station integrated into the whale back",
            ],
            composition_notes=[
                "station architecture grows naturally from the whale back"
            ],
            spatial_relations=[
                "garden rides on the whale back",
                "portal belongs to the carried station",
            ],
        ),
        layout_elements=[
            WorldLayoutElement(
                element_id="SCENE_WHALE",
                name="Gentle Sky Whale",
                kind="landmark",
                semantic_key="sky_whale",
                spatial_mode="aerial",
                elevation="high",
                geometry_role="organic",
                traversability="rideable",
                position=WorldPoint(x=30, y=12, z=30),
                width=18,
                depth=9,
                height=8,
            ),
            WorldLayoutElement(
                element_id="SCENE_GARDEN",
                name="Whale Back Garden Station",
                kind="terrain",
                semantic_key="whale_back_station",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="platform",
                traversability="walkable",
                position=WorldPoint(x=30, y=17, z=30),
                width=12,
                depth=7,
                height=2,
            ),
            WorldLayoutElement(
                element_id="SCENE_LIGHTHOUSE",
                name="Lighthouse Pavilion",
                kind="structure",
                semantic_key="lighthouse_pavilion",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="volume",
                traversability="scenic",
                position=WorldPoint(x=34, y=20, z=30),
                width=4,
                depth=4,
                height=6,
            ),
            WorldLayoutElement(
                element_id="SCENE_PORTAL",
                name="Moon Star Portal",
                kind="portal",
                semantic_key="moon_star_portal",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="arch",
                traversability="walkable",
                position=WorldPoint(x=25, y=19, z=31),
                width=5,
                depth=2,
                height=6,
            ),
            WorldLayoutElement(
                element_id="SCENE_SIGN",
                name="Cloud Sign",
                kind="decoration",
                semantic_key="cloud_sign",
                geometry_role="decorative",
                traversability="decorative",
                position=WorldPoint(x=8, y=0, z=8),
                width=2,
                depth=1,
                height=2,
            ),
        ],
    )


def _appearance() -> WorldAppearancePlan:
    objects = []
    for element_id, name, silhouette in [
        ("SCENE_WHALE", "Gentle Sky Whale", "organic_creature"),
        ("SCENE_GARDEN", "Whale Back Garden Station", "terrain"),
        ("SCENE_LIGHTHOUSE", "Lighthouse Pavilion", "architecture"),
        ("SCENE_PORTAL", "Moon Star Portal", "portal"),
        ("SCENE_SIGN", "Cloud Sign", "prop"),
    ]:
        objects.append(
            ObjectAppearanceSpec(
                element_id=element_id,
                name=name,
                silhouette_family=silhouette,
                silhouette_notes=f"storybook {name}",
                main_body=ShapePartSpec(
                    part_id=f"{element_id.lower()}_body",
                    role="main_body",
                    primitive="rounded_box" if element_id != "SCENE_WHALE" else "ellipsoid",
                ),
            )
        )
    return WorldAppearancePlan(
        world_style_summary="Warm whimsical storybook Mini Utopia",
        objects=objects,
    )


def _composition() -> WorldHeroCompositionPlan:
    return WorldHeroCompositionPlan.model_validate(
        {
            "source": "gpt",
            "clusters": [
                {
                    "cluster_id": "HERO_CLUSTER_CLOUD_WHALE_STATION",
                    "root_element_id": "SCENE_WHALE",
                    "render_strategy": "unified_glb",
                    "concept_summary": "One living flying whale station",
                    "members": [
                        {"element_id": "SCENE_WHALE", "role": "root"},
                        {
                            "element_id": "SCENE_GARDEN",
                            "role": "baked",
                            "relation_to_root": "on_top_of",
                        },
                        {
                            "element_id": "SCENE_LIGHTHOUSE",
                            "role": "baked",
                            "relation_to_root": "on_top_of",
                        },
                        {
                            "element_id": "SCENE_PORTAL",
                            "role": "baked",
                            "relation_to_root": "attached_to",
                        },
                    ],
                }
            ],
            "standalone_element_ids": ["SCENE_SIGN"],
        }
    )


def _render(blueprint, appearance):
    return WorldGeometryCompilerService().compile(
        profile=WorldProfile(
            world_name="Cloud Whale Station",
            source_description="A magical living whale station.",
        ),
        blueprint=blueprint,
        appearance=appearance,
        style_profile={},
    )


def test_unified_cluster_generates_one_reference_and_one_glb(tmp_path):
    blueprint = _blueprint()
    appearance = _appearance()
    ref_provider = CaptureReferenceProvider()
    hero_provider = CaptureHeroProvider()
    service = WorldHeroAssetService(
        storage=LocalObjectStorage(tmp_path / "storage"),
        provider=hero_provider,
        reference_image_provider=ref_provider,
    )

    enriched, builds, cache = service.enrich_render_spec(
        location_asset_id="LOC_CLOUD_WHALE",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=_render(blueprint, appearance),
        preview_image_bytes=_png(),
        preview_mime_type="image/png",
        composition_plan=_composition(),
        style_profile={
            "visual_dna_pillars": ["storybook toy world", "rounded forms"],
            "shape_language": "soft rounded silhouettes",
        },
    )

    assert len(ref_provider.calls) == 1
    prompt = ref_provider.calls[0]["prompt"]
    assert "ONE complete inseparable fantasy Hero composition" in prompt
    assert "92-96%" in prompt
    assert "bold, thick, readable toy-scale" in prompt
    assert "Whale Back Garden Station" in prompt
    assert "Lighthouse Pavilion" in prompt
    assert "Moon Star Portal" in prompt
    assert "NO unrelated world scenery" in prompt

    assert len(hero_provider.calls) == 1
    assert hero_provider.calls[0]["element_id"] == "HERO_CLUSTER_CLOUD_WHALE_STATION"
    assert len(builds) == 1
    build = builds[0]
    assert build.status == "generated"
    assert build.reference_mode == "generated_unified_cluster_v2"
    assert build.cluster_id == "HERO_CLUSTER_CLOUD_WHALE_STATION"
    assert set(build.member_element_ids) == {
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
        "SCENE_PORTAL",
    }
    assert build.usage["gpu_seconds"] == 42.0

    cache_key = "cluster:HERO_CLUSTER_CLOUD_WHALE_STATION"
    assert cache_key in cache
    assert cache[cache_key]["metadata"]["render_strategy"] == "unified_glb"
    assert cache[cache_key]["metadata"]["member_element_ids"] == list(
        build.member_element_ids
    )

    by_id = {item.element_id: item for item in enriched.objects}
    assert by_id["SCENE_WHALE"].visible is True
    assert any(
        node.geometry.source_type == "glb"
        for node in by_id["SCENE_WHALE"].nodes
    )
    assert by_id["SCENE_GARDEN"].visible is False
    assert by_id["SCENE_LIGHTHOUSE"].visible is False
    assert by_id["SCENE_PORTAL"].visible is False
    assert by_id["SCENE_SIGN"].visible is True


def test_old_root_only_cache_is_not_reused_for_unified_cluster(tmp_path):
    blueprint = _blueprint()
    appearance = _appearance()
    storage = LocalObjectStorage(tmp_path / "storage")
    storage.put_bytes("old-whale.glb", _glb())
    hero_provider = CaptureHeroProvider()
    service = WorldHeroAssetService(
        storage=storage,
        provider=hero_provider,
        reference_image_provider=CaptureReferenceProvider(),
    )

    _, builds, cache = service.enrich_render_spec(
        location_asset_id="LOC_CLOUD_WHALE",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=_render(blueprint, appearance),
        preview_image_bytes=_png(),
        preview_mime_type="image/png",
        composition_plan=_composition(),
        existing_assets={
            "SCENE_WHALE": {
                "asset_path": "old-whale.glb",
                "input_sha256": "legacy-single-object",
                "glb_sha256": "legacy",
                "bytes": len(_glb()),
                "metadata": {"reference_mode": "generated_isolated_v1"},
            }
        },
    )

    assert len(hero_provider.calls) == 1
    assert builds[0].status == "generated"
    assert builds[0].asset_path != "old-whale.glb"
    assert "cluster:HERO_CLUSTER_CLOUD_WHALE_STATION" in cache


def test_cluster_generation_failure_keeps_procedural_members_visible(tmp_path):
    blueprint = _blueprint()
    appearance = _appearance()
    service = WorldHeroAssetService(
        storage=LocalObjectStorage(tmp_path / "storage"),
        provider=CaptureHeroProvider(fail=True),
        reference_image_provider=CaptureReferenceProvider(),
    )

    enriched, builds, _ = service.enrich_render_spec(
        location_asset_id="LOC_CLOUD_WHALE",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=_render(blueprint, appearance),
        preview_image_bytes=_png(),
        preview_mime_type="image/png",
        composition_plan=_composition(),
    )

    assert builds[0].status == "fallback"
    by_id = {item.element_id: item for item in enriched.objects}
    assert all(by_id[element_id].visible for element_id in [
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
        "SCENE_PORTAL",
    ])
