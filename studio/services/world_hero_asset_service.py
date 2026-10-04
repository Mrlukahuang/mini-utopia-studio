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
from studio.providers.base import ImageGenerationProvider
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
    reference_mode: str = ""
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
        reference_image_provider: ImageGenerationProvider | None = None,
    ):
        self.storage = storage
        self.provider = provider
        self.max_assets_per_world = max(0, max_assets_per_world)
        self.reusable_library = reusable_library
        self.reference_image_provider = reference_image_provider

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
        profile=None,
        style_profile: dict | None = None,
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

            reference_mode, reference_fingerprint, reference_image, reference_prompt = (
                self._prepare_reference(
                    preview_image_bytes=preview_image_bytes,
                    appearance=item,
                    element=element,
                    style_profile=style_profile or {},
                )
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
                crop=reference_fingerprint,
                appearance=item,
                provider_key=provider_key,
                reference_mode=reference_mode,
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
                        reference_mode=str(
                            (cached.get("metadata", {}) or {}).get(
                                "reference_mode", reference_mode
                            )
                        ),
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
                                "reference_mode": reference_mode,
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
                                reference_mode=reference_mode,
                                message=(
                                    "Reused exact generated Hero from the global "
                                    "Mini Utopia Asset Library."
                                ),
                            )
                        )
                        continue

            try:
                if reference_image is None:
                    if not reference_prompt or self.reference_image_provider is None:
                        raise RuntimeError(
                            "Hero reference isolation could not produce a safe input image."
                        )
                    reference_image = self.reference_image_provider.generate(
                        prompt=reference_prompt,
                        size="1024x1024",
                        quality="medium",
                    )
                    reference_image = self._normalize_reference_image(reference_image)

                result = self.provider.generate(
                    image_bytes=reference_image,
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
                            source_url=str(result.metadata.get("space_url", "") or ""),
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
                        "reference_mode": reference_mode,
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
                        reference_mode=reference_mode,
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
                        reference_mode=reference_mode,
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
    def _has_localized_preview_bbox(appearance: ObjectAppearanceSpec) -> bool:
        bbox = appearance.preview_bbox
        area = bbox.width * bbox.height
        return bool(
            bbox.width >= 0.05
            and bbox.height >= 0.05
            and bbox.width <= 0.90
            and bbox.height <= 0.90
            and area <= 0.72
        )

    def _prepare_reference(
        self,
        *,
        preview_image_bytes: bytes,
        appearance: ObjectAppearanceSpec,
        element: WorldLayoutElement,
        style_profile: dict,
    ) -> tuple[str, bytes, bytes | None, str]:
        """Build a Hero-only image input instead of forwarding a whole World Preview."""
        if self._has_localized_preview_bbox(appearance):
            image = self._crop_preview(
                preview_image_bytes=preview_image_bytes,
                appearance=appearance,
            )
            image = self._normalize_reference_image(image)
            return "preview_bbox_isolated_v1", image, image, ""

        prompt = self._hero_reference_prompt(
            appearance=appearance,
            element=element,
            style_profile=style_profile,
        )
        if self.reference_image_provider is not None:
            return "generated_isolated_v1", prompt.encode("utf-8"), None, prompt

        image = self._center_focus_reference(preview_image_bytes)
        return "preview_center_fallback_v1", image, image, ""

    @staticmethod
    def _hero_reference_prompt(
        *,
        appearance: ObjectAppearanceSpec,
        element: WorldLayoutElement,
        style_profile: dict,
    ) -> str:
        parts = [appearance.main_body, *appearance.parts]
        part_lines = [
            (
                f"- {part.role}: shape={part.primitive}; "
                f"palette_role={part.palette_role}; material={part.material_role}; "
                f"surface={part.surface_detail or 'clean soft toy surface'}"
            )
            for part in parts[:12]
        ]
        visual_dna = ", ".join(style_profile.get("visual_dna_pillars", []))
        shape_language = style_profile.get("shape_language", "")
        material_language = style_profile.get(
            "runtime_material_rule",
            style_profile.get("material_language", ""),
        )
        return (
            "MINI UTOPIA HERO 3D REFERENCE IMAGE\n\n"
            f"Render exactly ONE object: {appearance.name}.\n"
            f"Semantic identity: {element.semantic_key or appearance.name}.\n"
            f"Silhouette family: {appearance.silhouette_family}.\n"
            f"Silhouette notes: {appearance.silhouette_notes or 'preserve a clear readable silhouette'}.\n"
            f"Detail density: {appearance.detail_density}.\n"
            f"Edge profile: {appearance.edge_profile}.\n"
            f"Symmetry: {appearance.symmetry}.\n"
            + ("Visual DNA: " + visual_dna + "\n" if visual_dna else "")
            + ("Shape language: " + shape_language + "\n" if shape_language else "")
            + ("Material language: " + material_language + "\n" if material_language else "")
            + "\nEXPLICIT PARTS\n"
            + "\n".join(part_lines)
            + "\n\nSTRICT ISOLATION RULES\n"
            + "- Show the complete object, centered, large, filling about 80-88% of a square frame.\n"
            + "- Use a clean three-quarter reference view that clearly reveals the main silhouette and appendages.\n"
            + "- Plain soft neutral studio background with clear separation from the object.\n"
            + "- NO environment, landscape, ground plane, platform, island, garden, plants, buildings, tower, station, bridge, portal, road, signs, labels, text, characters, vehicles, or unrelated props.\n"
            + "- Do not attach scenery to the object. Only include parts explicitly listed above.\n"
            + "- Keep Mini Utopia rounded toy-like stylization; avoid photorealism.\n"
            + "- This is a clean image-to-3D reference, not concept art and not a world scene."
        )

    @staticmethod
    def _normalize_reference_image(image_bytes: bytes, size: int = 1024) -> bytes:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        max_object = int(size * 0.88)
        image.thumbnail((max_object, max_object), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (246, 246, 248, 255))
        left = (size - image.width) // 2
        top = (size - image.height) // 2
        canvas.alpha_composite(image, (left, top))
        output = io.BytesIO()
        canvas.convert("RGB").save(output, format="PNG")
        return output.getvalue()

    @classmethod
    def _center_focus_reference(cls, preview_image_bytes: bytes) -> bytes:
        image = Image.open(io.BytesIO(preview_image_bytes)).convert("RGBA")
        width, height = image.size
        crop_w = max(1, int(width * 0.68))
        crop_h = max(1, int(height * 0.68))
        left = max(0, (width - crop_w) // 2)
        top = max(0, (height - crop_h) // 2)
        focused = image.crop((left, top, left + crop_w, top + crop_h))
        output = io.BytesIO()
        focused.save(output, format="PNG")
        return cls._normalize_reference_image(output.getvalue())

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

        # Tight context only: neighboring Blueprint objects must not be baked
        # into the generated Hero GLB.
        pad_x = max(.015, bbox.width * .04)
        pad_y = max(.015, bbox.height * .04)
        x0 = max(0.0, x0 - pad_x)
        y0 = max(0.0, y0 - pad_y)
        x1 = min(1.0, x1 + pad_x)
        y1 = min(1.0, y1 + pad_y)

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
        reference_mode: str = "legacy_preview_crop",
    ) -> str:
        digest = hashlib.sha256()
        digest.update(b"hero-reference-isolation-v1\0")
        digest.update(provider_key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(reference_mode.encode("utf-8"))
        digest.update(b"\0")
        digest.update(crop)
        appearance_payload = appearance.model_dump(mode="json")
        # Blueprint IDs identify placement, not visual geometry. Excluding the
        # element ID lets the same exact visual request be reused after a World
        # is cloned or rebuilt with a different local Scene ID.
        appearance_payload.pop("element_id", None)
        digest.update(
            json.dumps(
                appearance_payload,
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
