from __future__ import annotations

import io
import struct

from PIL import Image

from studio.models.render import (
    ObjectAppearanceSpec,
    ShapePartSpec,
    WorldAppearancePlan,
)
from studio.models.reusable_asset import ReusableAssetSourceSpec
from studio.models.world import WorldBlueprint, WorldLayoutElement, WorldPoint, WorldProfile
from studio.providers.hero_asset import HeroAssetProvider, HeroAssetResult
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.reusable_asset_library_service import ReusableAssetLibraryService
from studio.services.world_geometry_compiler_service import WorldGeometryCompilerService
from studio.services.world_hero_asset_service import WorldHeroAssetService
from studio.storage.local import LocalObjectStorage


def _glb() -> bytes:
    return b"glTF" + struct.pack("<II", 2, 12)


class NeverCalledProvider(HeroAssetProvider):
    model = "pixal3d"
    cache_identity = "fake:pixal3d:r1024"

    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return HeroAssetResult(
            payload=_glb(),
            mime_type="model/gltf-binary",
            model="pixal3d",
            provider="fake",
            metadata={},
        )


def _profile():
    return WorldProfile(
        world_name="Reuse World",
        source_description="A gentle sky whale.",
        world_type="Sky",
    )


def _blueprint():
    return WorldBlueprint(
        location_asset_id="LOC_REUSE",
        layout_elements=[
            WorldLayoutElement(
                element_id="SCENE_WHALE",
                name="Sky Whale",
                kind="landmark",
                semantic_key="sky_whale",
                geometry_role="organic",
                position=WorldPoint(x=10, y=5, z=10),
                width=12,
                depth=6,
                height=5,
            )
        ],
    )


def _appearance():
    return WorldAppearancePlan(
        world_style_summary="Mini Utopia",
        objects=[
            ObjectAppearanceSpec(
                element_id="SCENE_WHALE",
                name="Sky Whale",
                silhouette_family="organic_creature",
                main_body=ShapePartSpec(
                    part_id="body",
                    role="main_body",
                    primitive="ellipsoid",
                ),
            )
        ],
    )


def _preview():
    image = Image.new("RGBA", (64, 64), (220, 235, 255, 255))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_world_hero_service_reuses_exact_global_generated_asset(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    library = ReusableAssetLibraryService(repo, storage)
    provider = NeverCalledProvider()
    appearance = _appearance()
    blueprint = _blueprint()

    compiler = WorldGeometryCompilerService()
    render = compiler.compile(
        profile=_profile(),
        blueprint=blueprint,
        appearance=appearance,
        style_profile={},
    )

    probe = WorldHeroAssetService(
        storage=storage,
        provider=provider,
        reusable_library=library,
    )
    element = blueprint.layout_elements[0]
    reference_mode, fingerprint, _, _ = probe._prepare_reference(
        preview_image_bytes=_preview(),
        appearance=appearance.objects[0],
        element=element,
        style_profile={},
    )
    input_sha = probe._input_sha(
        crop=fingerprint,
        appearance=appearance.objects[0],
        provider_key=provider.cache_identity,
        reference_mode=reference_mode,
    )

    library.import_glb(
        payload=_glb(),
        display_name="Existing Sky Whale",
        category="hero",
        semantic_keys=["sky_whale", "hero"],
        source=ReusableAssetSourceSpec(
            origin_kind="generated",
            source_name="huggingface_space",
            generator_model="pixal3d",
            license_id="GENERATED",
        ),
        source_fingerprint=input_sha,
    )

    enriched, builds, cache = probe.enrich_render_spec(
        location_asset_id="LOC_REUSE",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=render,
        preview_image_bytes=_preview(),
        preview_mime_type="image/png",
    )

    assert provider.calls == 0
    assert builds[0].status == "cached"
    assert "global" in builds[0].message
    assert cache["SCENE_WHALE"]["metadata"]["reused_from_library"] is True
    whale = enriched.objects[0]
    assert any(node.geometry.source_type == "glb" for node in whale.nodes)



def test_first_generation_enters_global_library_and_second_world_reuses_it(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    library = ReusableAssetLibraryService(repo, storage)
    provider = NeverCalledProvider()
    appearance = _appearance()
    blueprint = _blueprint()
    compiler = WorldGeometryCompilerService()
    service = WorldHeroAssetService(
        storage=storage,
        provider=provider,
        reusable_library=library,
    )

    first_render = compiler.compile(
        profile=_profile(),
        blueprint=blueprint,
        appearance=appearance,
        style_profile={},
    )
    first, first_builds, _ = service.enrich_render_spec(
        location_asset_id="LOC_FIRST",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=first_render,
        preview_image_bytes=_preview(),
        preview_mime_type="image/png",
    )

    assert provider.calls == 1
    assert first_builds[0].status == "generated"
    reusable = library.list_reusable()
    assert len(reusable) == 1
    reusable_spec = library.get_spec(reusable[0])
    assert reusable_spec.category == "hero"
    assert reusable_spec.source.generator_model == "pixal3d"
    assert reusable_spec.source_fingerprint == first_builds[0].input_sha256

    second_render = compiler.compile(
        profile=_profile(),
        blueprint=blueprint,
        appearance=appearance,
        style_profile={},
    )
    second, second_builds, _ = service.enrich_render_spec(
        location_asset_id="LOC_SECOND",
        blueprint=blueprint,
        appearance=appearance,
        render_spec=second_render,
        preview_image_bytes=_preview(),
        preview_mime_type="image/png",
    )

    assert provider.calls == 1
    assert second_builds[0].status == "cached"
    assert second_builds[0].asset_path == reusable_spec.storage_path
    assert any(
        node.geometry.asset_path == reusable_spec.storage_path
        for node in second.objects[0].nodes
        if node.geometry.source_type == "glb"
    )
