from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass

from PIL import Image

from studio.models.render import (
    ObjectAppearanceSpec,
    RenderVec3,
    ThreeGeometrySpec,
    ThreeMeshNodeSpec,
    WorldAppearancePlan,
    WorldRenderSpec,
)
from studio.models.world import WorldBlueprint, WorldLayoutElement
from studio.providers.hero_asset import HeroAssetProvider
from studio.models.reusable_asset import ReusableAssetSourceSpec
from studio.services.reusable_asset_library_service import ReusableAssetLibraryService
from studio.storage.base import ObjectStorage


@dataclass(frozen=True)
class HeroAssetBuild:
    element_id: str
    name: str
    status: str
    asset_path: str = ""
    model: str = ""
    input_sha256: str = ""
    glb_sha256: str = ""
    bytes: int = 0
    message: str = ""


class WorldHeroAssetService:
    """Generate one high-value Hero GLB while keeping Blueprint authoritative."""

    def __init__(
        self,
        *,
        storage: ObjectStorage,
        provider: HeroAssetProvider | None,
        max_assets_per_world: int = 1,
        reusable_library: ReusableAssetLibraryService | None = None,
    ):
        self.storage = storage
        self.provider = provider
        self.max_assets_per_world = max(0, max_assets_per_world)
        self.reusable_library = reusable_library

    @property
    def is_available(self) -> bool:
        return self.provider is not None and self.max_assets_per_world > 0

    def enrich_render_spec(
        self,
        *,
        location_asset_id: str,
        blueprint: WorldBlueprint,
        appearance: WorldAppearancePlan,
        render_spec: WorldRenderSpec,
        preview_image_bytes: bytes,
        preview_mime_type: str,
        existing_assets: dict | None = None,
    ) -> tuple[WorldRenderSpec, list[HeroAssetBuild], dict]:
        if not self.is_available:
            return render_spec, [], existing_assets or {}

        appearance_by_id = {item.element_id: item for item in appearance.objects}
        candidates = [
            element
            for element in blueprint.layout_elements
            if self._is_hero_candidate(
                element=element,
                appearance=appearance_by_id.get(element.element_id),
            )
        ]
        candidates.sort(
            key=lambda element: (
                element.width * element.depth * element.height,
                max(element.width, element.depth, element.height),
            ),
            reverse=True,
        )
        candidates = candidates[: self.max_assets_per_world]

        updated = render_spec.model_copy(deep=True)
        updated_by_id = {item.element_id: item for item in updated.objects}
        cache = dict(existing_assets or {})
        builds: list[HeroAssetBuild] = []

        for element in candidates:
            item = appearance_by_id.get(element.element_id)
            render_object = updated_by_id.get(element.element_id)
            if item is None or render_object is None:
                continue

            crop = self._crop_preview(
                preview_image_bytes=preview_image_bytes,
                appearance=item,
            )
            provider_key = str(
                getattr(
                    self.provider,
                    "cache_identity",
                    getattr(
                        self.provider,
                        "model",
                        self.provider.__class__.__name__,
                    ),
                )
            )
            input_sha = self._input_sha(
                crop=crop,
                appearance=item,
                provider_key=provider_key,
            )
            cached = cache.get(element.element_id, {}) or {}
            cached_path = str(cached.get("asset_path", "") or "")
            if (
                cached.get("input_sha256") == input_sha
                and cached_path
                and self.storage.exists(cached_path)
            ):
                self._attach_glb_node(
                    render_object=render_object,
                    element=element,
                    asset_path=cached_path,
                    asset_sha256=str(cached.get("glb_sha256", "") or ""),
                    model=str(cached.get("model", "") or "cached"),
                )
                builds.append(
                    HeroAssetBuild(
                        element_id=element.element_id,
                        name=element.name,
                        status="cached",
                        asset_path=cached_path,
                        model=str(cached.get("model", "") or "cached"),
                        input_sha256=input_sha,
                        glb_sha256=str(cached.get("glb_sha256", "") or ""),
                        bytes=int(cached.get("bytes", 0) or 0),
                    )
                )
                continue

            if self.reusable_library is not None:
                reusable = self.reusable_library.find_by_source_fingerprint(input_sha)
                if reusable is not None:
                    reusable_spec = self.reusable_library.get_spec(reusable)
                    if self.storage.exists(reusable_spec.storage_path):
                        self._attach_glb_node(
                            render_object=render_object,
                            element=element,
                            asset_path=reusable_spec.storage_path,
                            asset_sha256=reusable_spec.sha256,
                            model=reusable_spec.source.generator_model or "library",
                        )
                        cache[element.element_id] = {
                            "asset_path": reusable_spec.storage_path,
                            "mime_type": "model/gltf-binary",
                            "model": reusable_spec.source.generator_model or "library",
                            "provider": reusable_spec.source.source_name,
                            "input_sha256": input_sha,
                            "glb_sha256": reusable_spec.sha256,
                            "bytes": reusable_spec.byte_size,
                            "metadata": {
                                "reusable_asset_id": reusable.asset_id,
                                "reused_from_library": True,
                            },
                        }
                        builds.append(
                            HeroAssetBuild(
                                element_id=element.element_id,
                                name=element.name,
                                status="cached",
                                asset_path=reusable_spec.storage_path,
                                model=reusable_spec.source.generator_model or "library",
                                input_sha256=input_sha,
                                glb_sha256=reusable_spec.sha256,
                                bytes=reusable_spec.byte_size,
                                message=(
                                    "Reused exact generated Hero from the global "
                                    "Mini Utopia Asset Library."
                                ),
                            )
                        )
                        continue

            try:
                result = self.provider.generate(
                    image_bytes=crop,
                    mime_type="image/png",
                    element_id=element.element_id,
                    appearance=item,
                )
                glb_sha = hashlib.sha256(result.payload).hexdigest()
                reusable_asset_id = ""
                if self.reusable_library is not None:
                    reusable = self.reusable_library.import_glb(
                        payload=result.payload,
                        display_name=f"{element.name} / Generated Hero",
                        category="hero",
                        semantic_keys=list(
                            dict.fromkeys(
                                [
                                    element.semantic_key,
                                    item.silhouette_family,
                                    "hero",
                                ]
                            )
                        ),
                        source=ReusableAssetSourceSpec(
                            origin_kind="generated",
                            source_name=result.provider,
                            source_url=str(result.metadata.get("space_id", "") or ""),
                            license_id="GENERATED",
                            attribution_required=False,
                            generator_model=result.model,
                        ),
                        tags=["generated-hero", "mini-utopia"],
                        source_fingerprint=input_sha,
                    )
                    reusable_spec = self.reusable_library.get_spec(reusable)
                    asset_path = reusable_spec.storage_path
                    reusable_asset_id = reusable.asset_id
                else:
                    asset_path = self.storage.put_bytes(
                        (
                            f"assets/{location_asset_id}/hero/"
                            f"{element.element_id}_{glb_sha[:12]}.glb"
                        ),
                        result.payload,
                    )
                cache[element.element_id] = {
                    "asset_path": asset_path,
                    "mime_type": result.mime_type,
                    "model": result.model,
                    "provider": result.provider,
                    "input_sha256": input_sha,
                    "glb_sha256": glb_sha,
                    "bytes": len(result.payload),
                    "metadata": {
                        **result.metadata,
                        **(
                            {"reusable_asset_id": reusable_asset_id}
                            if reusable_asset_id
                            else {}
                        ),
                    },
                }
                self._attach_glb_node(
                    render_object=render_object,
                    element=element,
                    asset_path=asset_path,
                    asset_sha256=glb_sha,
                    model=result.model,
                )
                builds.append(
                    HeroAssetBuild(
                        element_id=element.element_id,
                        name=element.name,
                        status="generated",
                        asset_path=asset_path,
                        model=result.model,
                        input_sha256=input_sha,
                        glb_sha256=glb_sha,
                        bytes=len(result.payload),
                    )
                )
            except Exception as exc:
                # Hero GLB is a quality upgrade. Procedural nodes remain intact
                # so Explore still works if the experimental GPU Worker fails.
                builds.append(
                    HeroAssetBuild(
                        element_id=element.element_id,
                        name=element.name,
                        status="fallback",
                        input_sha256=input_sha,
                        message=str(exc),
                    )
                )

        return updated, builds, cache

    def attach_existing_glb(
        self,
        *,
        location_asset_id: str,
        blueprint: WorldBlueprint,
        render_spec: WorldRenderSpec,
        element_id: str,
        payload: bytes,
        model: str = "manual_glb",
    ) -> tuple[WorldRenderSpec, HeroAssetBuild, dict]:
        if not payload:
            raise ValueError("Hero GLB payload is empty.")

        element = next(
            (
                item
                for item in blueprint.layout_elements
                if item.element_id == element_id
            ),
            None,
        )
        if element is None:
            raise ValueError(f"Blueprint element not found: {element_id}")

        updated = render_spec.model_copy(deep=True)
        render_object = next(
            (
                item
                for item in updated.objects
                if item.element_id == element_id
            ),
            None,
        )
        if render_object is None:
            raise ValueError(f"RenderSpec object not found: {element_id}")

        glb_sha = hashlib.sha256(payload).hexdigest()
        asset_path = self.storage.put_bytes(
            (
                f"assets/{location_asset_id}/hero/"
                f"{element_id}_{glb_sha[:12]}.glb"
            ),
            payload,
        )
        self._attach_glb_node(
            render_object=render_object,
            element=element,
            asset_path=asset_path,
            asset_sha256=glb_sha,
            model=model,
        )
        record = {
            "asset_path": asset_path,
            "mime_type": "model/gltf-binary",
            "model": model,
            "provider": "manual",
            "input_sha256": f"manual:{glb_sha}",
            "glb_sha256": glb_sha,
            "bytes": len(payload),
            "metadata": {},
        }
        build = HeroAssetBuild(
            element_id=element_id,
            name=element.name,
            status="generated",
            asset_path=asset_path,
            model=model,
            input_sha256=record["input_sha256"],
            glb_sha256=glb_sha,
            bytes=len(payload),
            message="Manual GLB attached for Hero pipeline validation.",
        )
        return updated, build, record

    @staticmethod
    def _is_hero_candidate(
        *,
        element: WorldLayoutElement,
        appearance: ObjectAppearanceSpec | None,
    ) -> bool:
        if appearance is None:
            return False
        organic = (
            element.geometry_role == "organic"
            or appearance.silhouette_family == "organic_creature"
        )
        major = (
            element.kind in {"landmark", "structure"}
            and max(element.width, element.depth, element.height) >= 6.0
        )
        return bool(organic and major)

    @staticmethod
    def _crop_preview(
        *,
        preview_image_bytes: bytes,
        appearance: ObjectAppearanceSpec,
    ) -> bytes:
        image = Image.open(io.BytesIO(preview_image_bytes)).convert("RGBA")
        width, height = image.size
        bbox = appearance.preview_bbox

        x0 = bbox.x
        y0 = bbox.y
        x1 = bbox.x + bbox.width
        y1 = bbox.y + bbox.height

        # Give the image-to-3D model a little context around the visible Hero.
        pad_x = max(.03, bbox.width * .08)
        pad_y = max(.03, bbox.height * .08)
        x0 = max(0.0, x0 - pad_x)
        y0 = max(0.0, y0 - pad_y)
        x1 = min(1.0, x1 + pad_x)
        y1 = min(1.0, y1 + pad_y)

        # Vision may leave the default full-frame bbox. That is still a legal
        # spike input; the Worker performs its own foreground segmentation.
        left = max(0, min(width - 1, int(round(x0 * width))))
        top = max(0, min(height - 1, int(round(y0 * height))))
        right = max(left + 1, min(width, int(round(x1 * width))))
        bottom = max(top + 1, min(height, int(round(y1 * height))))

        cropped = image.crop((left, top, right, bottom))
        output = io.BytesIO()
        cropped.save(output, format="PNG")
        return output.getvalue()

    @staticmethod
    def _input_sha(
        *,
        crop: bytes,
        appearance: ObjectAppearanceSpec,
        provider_key: str,
    ) -> str:
        digest = hashlib.sha256()
        digest.update(provider_key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(crop)
        digest.update(
            json.dumps(
                appearance.model_dump(mode="json"),
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        )
        return digest.hexdigest()

    @staticmethod
    def _attach_glb_node(
        *,
        render_object,
        element: WorldLayoutElement,
        asset_path: str,
        asset_sha256: str,
        model: str,
    ) -> None:
        node_id = f"{element.element_id}:hero_glb"
        render_object.nodes = [
            node for node in render_object.nodes
            if node.node_id != node_id
        ]
        render_object.nodes.append(
            ThreeMeshNodeSpec(
                node_id=node_id,
                geometry=ThreeGeometrySpec(
                    source_type="glb",
                    asset_path=asset_path,
                    asset_mime_type="model/gltf-binary",
                    asset_sha256=asset_sha256,
                ),
                material_id="",
                local_position=RenderVec3(),
                cast_shadow=True,
                receive_shadow=True,
            )
        )
        render_object.animation_clip_names = [
            name
            for name in [*render_object.animation_clip_names, f"source:{model}"]
            if name
        ][:16]
