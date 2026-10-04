from __future__ import annotations

import io
import struct

from PIL import Image

from studio.models.render import (
    ObjectAppearanceSpec,
    PreviewBBox,
    ShapePartSpec,
    WorldAppearancePlan,
)
from studio.models.world import WorldBlueprint, WorldLayoutElement, WorldPoint, WorldProfile
from studio.providers.base import ImageGenerationProvider
from studio.providers.hero_asset import HeroAssetProvider, HeroAssetResult
from studio.services.world_geometry_compiler_service import WorldGeometryCompilerService
from studio.services.world_hero_asset_service import WorldHeroAssetService
from studio.storage.local import LocalObjectStorage


def _png(size=(960, 640), color=(180, 210, 240, 255)) -> bytes:
    image = Image.new("RGBA", size, color)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _glb() -> bytes:
    return b"glTF" + struct.pack("<II", 2, 12)


class CaptureHeroProvider(HeroAssetProvider):
    model = "pixal3d"
    cache_identity = "fake:pixal3d:r1024"

    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return HeroAssetResult(
            payload=_glb(),
            mime_type="model/gltf-binary",
            model="pixal3d",
            provider="fake",
            metadata={},
        )


class FakeReferenceImageProvider(ImageGenerationProvider):
    def __init__(self):
        self.calls = []

    def generate(self, *, prompt: str, size: str = "1024x1536", quality: str = "medium") -> bytes:
        self.calls.append({"prompt": prompt, "size": size, "quality": quality})
        return _png((640, 900), (120, 160, 220, 255))


def _blueprint() -> WorldBlueprint:
    return WorldBlueprint(
        location_asset_id="LOC_HERO_ISOLATION",
        layout_elements=[
            WorldLayoutElement(
                element_id="SCENE_WHALE",
                name="Gentle Sky Whale",
                kind="landmark",
                semantic_key="sky_whale",
                geometry_role="organic",
                position=WorldPoint(x=30, y=14, z=30),
                width=14,
                depth=7,
                height=6,
            )
        ],
    )


def _appearance(*, localized: bool = False) -> WorldAppearancePlan:
    return WorldAppearancePlan(
        world_style_summary="Mini Utopia",
        objects=[
            ObjectAppearanceSpec(
                element_id="SCENE_WHALE",
                name="Gentle Sky Whale",
                silhouette_family="organic_creature",
                silhouette_notes="friendly blue whale with rounded body, fins and tail flukes",
                detail_density="high",
                main_body=ShapePartSpec(
                    part_id="body",
                    role="main_body",
                    primitive="ellipsoid",
                    surface_detail="soft subtle skin grooves",
                ),
                parts=[
                    ShapePartSpec(
                        part_id="tail",
                        role="tail_fluke",
                        primitive="wedge",
                    ),
                    ShapePartSpec(
                        part_id="fin",
                        role="pectoral_fin",
                        primitive="wedge",
                    ),
                ],
                preview_bbox=(
                    PreviewBBox(x=0.2, y=0.18, width=0.48, height=0.42)
                    if localized
                    else PreviewBBox()
                ),
            )
        ],
    )


def _render(blueprint: WorldBlueprint, appearance: WorldAppearancePlan):
    return WorldGeometryCompilerService().compile(
        profile=WorldProfile(world_name="Whale World"),
        blueprint=blueprint,
        appearance=appearance,
        style_profile={},
    )


def test_full_frame_bbox_generates_dedicated_isolated_reference(tmp_path):
    blueprint = _blueprint()
    appearance = _appearance(localized=False)
    hero_provider = CaptureHeroProvider()
    reference_provider = FakeReferenceImageProvider()
    service = WorldHeroAssetService(
        storage=LocalObjectStorage(tmp_path / "storage"),
        provider=hero_provider,
        reference_image_provider=reference_provider,
    )

    _, builds, cache = service.enrich_render_spec(
        location_asset_id="LOC_HERO_ISOLATION",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=_render(blueprint, appearance),
        preview_image_bytes=_png(),
        preview_mime_type="image/png",
        style_profile={
            "visual_dna_pillars": ["rounded toy forms", "macaron dreamscape"],
            "shape_language": "soft rounded forms",
        },
    )

    assert len(reference_provider.calls) == 1
    request = reference_provider.calls[0]
    assert request["size"] == "1024x1024"
    assert "Render exactly ONE object: Gentle Sky Whale" in request["prompt"]
    assert "NO environment" in request["prompt"]
    assert "portal" in request["prompt"]
    assert "garden" in request["prompt"]

    assert len(hero_provider.calls) == 1
    sent = Image.open(io.BytesIO(hero_provider.calls[0]["image_bytes"]))
    assert sent.size == (1024, 1024)
    assert builds[0].status == "generated"
    assert builds[0].reference_mode == "generated_isolated_v1"
    assert cache["SCENE_WHALE"]["metadata"]["reference_mode"] == "generated_isolated_v1"


def test_localized_vision_bbox_uses_tight_preview_crop_without_second_image_call(tmp_path):
    blueprint = _blueprint()
    appearance = _appearance(localized=True)
    hero_provider = CaptureHeroProvider()
    reference_provider = FakeReferenceImageProvider()
    service = WorldHeroAssetService(
        storage=LocalObjectStorage(tmp_path / "storage"),
        provider=hero_provider,
        reference_image_provider=reference_provider,
    )

    _, builds, _ = service.enrich_render_spec(
        location_asset_id="LOC_HERO_CROP",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=_render(blueprint, appearance),
        preview_image_bytes=_png(),
        preview_mime_type="image/png",
        style_profile={},
    )

    assert reference_provider.calls == []
    assert len(hero_provider.calls) == 1
    sent = Image.open(io.BytesIO(hero_provider.calls[0]["image_bytes"]))
    assert sent.size == (1024, 1024)
    assert builds[0].reference_mode == "preview_bbox_isolated_v1"


def test_no_reference_generator_never_forwards_the_full_world_preview(tmp_path):
    blueprint = _blueprint()
    appearance = _appearance(localized=False)
    hero_provider = CaptureHeroProvider()
    original = _png()
    service = WorldHeroAssetService(
        storage=LocalObjectStorage(tmp_path / "storage"),
        provider=hero_provider,
        reference_image_provider=None,
    )

    _, builds, _ = service.enrich_render_spec(
        location_asset_id="LOC_HERO_SAFE_FALLBACK",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=_render(blueprint, appearance),
        preview_image_bytes=original,
        preview_mime_type="image/png",
        style_profile={},
    )

    assert len(hero_provider.calls) == 1
    assert hero_provider.calls[0]["image_bytes"] != original
    sent = Image.open(io.BytesIO(hero_provider.calls[0]["image_bytes"]))
    assert sent.size == (1024, 1024)
    assert builds[0].reference_mode == "preview_center_fallback_v1"
