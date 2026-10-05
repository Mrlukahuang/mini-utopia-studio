from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass

from PIL import Image

from studio.models.hero_composition import (
    HeroCompositionCluster,
    WorldHeroCompositionPlan,
)
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
    usage: dict | None = None
    message: str = ""
    cluster_id: str = ""
    member_element_ids: tuple[str, ...] = ()
    target_size: tuple[float, float, float] | None = None


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
        composition_plan: WorldHeroCompositionPlan | None = None,
    ) -> tuple[WorldRenderSpec, list[HeroAssetBuild], dict]:
        if not self.is_available:
            return render_spec, [], existing_assets or {}

        appearance_by_id = {item.element_id: item for item in appearance.objects}
        if composition_plan is not None and composition_plan.clusters:
            return self._enrich_unified_clusters(
                location_asset_id=location_asset_id,
                blueprint=blueprint,
                appearance=appearance,
                render_spec=render_spec,
                style_profile=style_profile or {},
                existing_assets=existing_assets,
                composition_plan=composition_plan,
            )

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
                        usage=(
                            (cached.get("metadata", {}) or {}).get(
                                "zero_gpu_usage"
                            )
                            or self.provider.usage_snapshot()
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
                                usage=self.provider.usage_snapshot(),
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
                        usage=result.metadata.get("zero_gpu_usage"),
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
                        usage=self.provider.usage_snapshot(),
                        message=str(exc),
                    )
                )

        return updated, builds, cache

    def _enrich_unified_clusters(
        self,
        *,
        location_asset_id: str,
        blueprint: WorldBlueprint,
        appearance: WorldAppearancePlan,
        render_spec: WorldRenderSpec,
        style_profile: dict,
        existing_assets: dict | None,
        composition_plan: WorldHeroCompositionPlan,
    ) -> tuple[WorldRenderSpec, list[HeroAssetBuild], dict]:
        """Generate each selected Hero cluster as one inseparable GLB."""
        appearance_by_id = {item.element_id: item for item in appearance.objects}
        element_by_id = {item.element_id: item for item in blueprint.layout_elements}
        updated = render_spec.model_copy(deep=True)
        updated_by_id = {item.element_id: item for item in updated.objects}
        cache = dict(existing_assets or {})
        builds: list[HeroAssetBuild] = []

        clusters = composition_plan.clusters[: self.max_assets_per_world]
        provider_key = str(
            getattr(
                self.provider,
                "cache_identity",
                getattr(self.provider, "model", self.provider.__class__.__name__),
            )
        )

        for cluster in clusters:
            root = element_by_id.get(cluster.root_element_id)
            root_appearance = appearance_by_id.get(cluster.root_element_id)
            render_object = updated_by_id.get(cluster.root_element_id)
            if root is None or root_appearance is None or render_object is None:
                continue

            member_ids = tuple(
                member.element_id
                for member in cluster.members
                if member.element_id in element_by_id
            )
            if cluster.root_element_id not in member_ids:
                member_ids = (cluster.root_element_id, *member_ids)

            reference_mode, reference_fingerprint, reference_prompt = (
                self._prepare_cluster_reference(
                    cluster=cluster,
                    blueprint=blueprint,
                    appearance_by_id=appearance_by_id,
                    style_profile=style_profile,
                )
            )
            input_sha = self._cluster_input_sha(
                reference_fingerprint=reference_fingerprint,
                cluster=cluster,
                member_ids=member_ids,
                appearance_by_id=appearance_by_id,
                provider_key=provider_key,
                reference_mode=reference_mode,
                visual_anchor=blueprint.visual_anchor.model_dump(mode="json"),
            )
            cache_key = f"cluster:{cluster.cluster_id}"
            target_size = self._cluster_target_size(
                member_ids=member_ids,
                element_by_id=element_by_id,
            )
            cached = cache.get(cache_key, {}) or {}
            cached_path = str(cached.get("asset_path", "") or "")

            if (
                cached.get("input_sha256") == input_sha
                and cached_path
                and self.storage.exists(cached_path)
            ):
                self._attach_glb_node(
                    render_object=render_object,
                    element=root,
                    asset_path=cached_path,
                    asset_sha256=str(cached.get("glb_sha256", "") or ""),
                    model=str(cached.get("model", "") or "cached"),
                )
                self._suppress_baked_members(
                    updated_by_id=updated_by_id,
                    cluster=cluster,
                )
                builds.append(
                    HeroAssetBuild(
                        element_id=root.element_id,
                        name=root.name,
                        status="cached",
                        asset_path=cached_path,
                        model=str(cached.get("model", "") or "cached"),
                        input_sha256=input_sha,
                        glb_sha256=str(cached.get("glb_sha256", "") or ""),
                        bytes=int(cached.get("bytes", 0) or 0),
                        reference_mode=reference_mode,
                        usage=(
                            (cached.get("metadata", {}) or {}).get("zero_gpu_usage")
                            or self.provider.usage_snapshot()
                        ),
                        message="Reused exact unified Hero Cluster cache.",
                        cluster_id=cluster.cluster_id,
                        member_element_ids=member_ids,
                        target_size=target_size,
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
                            element=root,
                            asset_path=reusable_spec.storage_path,
                            asset_sha256=reusable_spec.sha256,
                            model=reusable_spec.source.generator_model or "library",
                        )
                        self._suppress_baked_members(
                            updated_by_id=updated_by_id,
                            cluster=cluster,
                        )
                        cache[cache_key] = {
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
                                "cluster_id": cluster.cluster_id,
                                "member_element_ids": list(member_ids),
                                "render_strategy": "unified_glb",
                            },
                        }
                        builds.append(
                            HeroAssetBuild(
                                element_id=root.element_id,
                                name=root.name,
                                status="cached",
                                asset_path=reusable_spec.storage_path,
                                model=reusable_spec.source.generator_model or "library",
                                input_sha256=input_sha,
                                glb_sha256=reusable_spec.sha256,
                                bytes=reusable_spec.byte_size,
                                reference_mode=reference_mode,
                                usage=self.provider.usage_snapshot(),
                                message="Reused exact unified Hero Cluster from global library.",
                                cluster_id=cluster.cluster_id,
                                member_element_ids=member_ids,
                                target_size=target_size,
                            )
                        )
                        continue

            try:
                if self.reference_image_provider is None:
                    raise RuntimeError(
                        "Unified Hero Cluster needs a dedicated reference image provider; "
                        "the whole World Preview will not be forwarded to Pixal3D."
                    )

                reference_image = self.reference_image_provider.generate(
                    prompt=reference_prompt,
                    size="1536x1024",
                    quality="medium",
                )
                reference_image = self._normalize_reference_image(
                    reference_image,
                    size=1536,
                    max_fill=0.96,
                )

                result = self.provider.generate(
                    image_bytes=reference_image,
                    mime_type="image/png",
                    element_id=cluster.cluster_id,
                    appearance=root_appearance,
                )
                glb_sha = hashlib.sha256(result.payload).hexdigest()
                reusable_asset_id = ""

                semantic_keys = [
                    element_by_id[element_id].semantic_key
                    for element_id in member_ids
                    if element_by_id[element_id].semantic_key
                ]
                if self.reusable_library is not None:
                    reusable = self.reusable_library.import_glb(
                        payload=result.payload,
                        display_name=f"{root.name} / Unified Hero Cluster",
                        category="hero",
                        semantic_keys=list(
                            dict.fromkeys([*semantic_keys, "hero", "hero-cluster"])
                        ),
                        source=ReusableAssetSourceSpec(
                            origin_kind="generated",
                            source_name=result.provider,
                            source_url=str(result.metadata.get("space_url", "") or ""),
                            license_id="GENERATED",
                            attribution_required=False,
                            generator_model=result.model,
                        ),
                        tags=["generated-hero", "hero-cluster", "mini-utopia"],
                        source_fingerprint=input_sha,
                    )
                    reusable_spec = self.reusable_library.get_spec(reusable)
                    asset_path = reusable_spec.storage_path
                    reusable_asset_id = reusable.asset_id
                else:
                    safe_cluster_id = cluster.cluster_id.replace("/", "_")
                    asset_path = self.storage.put_bytes(
                        (
                            f"assets/{location_asset_id}/hero_cluster/"
                            f"{safe_cluster_id}_{glb_sha[:12]}.glb"
                        ),
                        result.payload,
                    )

                usage = (
                    result.metadata.get("zero_gpu_usage")
                    or self.provider.usage_snapshot()
                )
                cache[cache_key] = {
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
                        "cluster_id": cluster.cluster_id,
                        "member_element_ids": list(member_ids),
                        "render_strategy": "unified_glb",
                        **(
                            {"reusable_asset_id": reusable_asset_id}
                            if reusable_asset_id
                            else {}
                        ),
                    },
                }
                self._attach_glb_node(
                    render_object=render_object,
                    element=root,
                    asset_path=asset_path,
                    asset_sha256=glb_sha,
                    model=result.model,
                )
                self._suppress_baked_members(
                    updated_by_id=updated_by_id,
                    cluster=cluster,
                )
                builds.append(
                    HeroAssetBuild(
                        element_id=root.element_id,
                        name=root.name,
                        status="generated",
                        asset_path=asset_path,
                        model=result.model,
                        input_sha256=input_sha,
                        glb_sha256=glb_sha,
                        bytes=len(result.payload),
                        reference_mode=reference_mode,
                        usage=usage,
                        message=(
                            "Generated as one unified Hero Cluster GLB."
                            + (
                                " Quality fallback: "
                                + "; ".join(
                                    str(item.get("stage", "provider"))
                                    for item in result.metadata.get(
                                        "quality_fallbacks", []
                                    )
                                )
                                if result.metadata.get("quality_fallbacks")
                                else ""
                            )
                        ),
                        cluster_id=cluster.cluster_id,
                        member_element_ids=member_ids,
                        target_size=target_size,
                    )
                )
            except Exception as exc:
                builds.append(
                    HeroAssetBuild(
                        element_id=root.element_id,
                        name=root.name,
                        status="fallback",
                        input_sha256=input_sha,
                        reference_mode=reference_mode,
                        usage=self.provider.usage_snapshot(),
                        message=str(exc),
                        cluster_id=cluster.cluster_id,
                        member_element_ids=member_ids,
                        target_size=target_size,
                    )
                )

        return updated, builds, cache

    def _prepare_cluster_reference(
        self,
        *,
        cluster: HeroCompositionCluster,
        blueprint: WorldBlueprint,
        appearance_by_id: dict[str, ObjectAppearanceSpec],
        style_profile: dict,
    ) -> tuple[str, bytes, str]:
        prompt = self._hero_cluster_reference_prompt(
            cluster=cluster,
            blueprint=blueprint,
            appearance_by_id=appearance_by_id,
            style_profile=style_profile,
        )
        return (
            "generated_unified_cluster_v2",
            prompt.encode("utf-8"),
            prompt,
        )

    @staticmethod
    def _hero_cluster_reference_prompt(
        *,
        cluster: HeroCompositionCluster,
        blueprint: WorldBlueprint,
        appearance_by_id: dict[str, ObjectAppearanceSpec],
        style_profile: dict,
    ) -> str:
        element_by_id = {item.element_id: item for item in blueprint.layout_elements}
        member_lines: list[str] = []
        for member in cluster.members:
            element = element_by_id.get(member.element_id)
            if element is None:
                continue
            appearance = appearance_by_id.get(member.element_id)
            appearance_note = ""
            if appearance is not None:
                appearance_note = (
                    f"; silhouette={appearance.silhouette_family}; "
                    f"notes={appearance.silhouette_notes or appearance.name}"
                )
            member_lines.append(
                (
                    f"- {member.role.upper()} · {element.name} "
                    f"[{element.element_id}] · semantic={element.semantic_key or element.name}; "
                    f"kind={element.kind}; geometry={element.geometry_role}; "
                    f"relation={member.relation_to_root or 'root composition'}"
                    f"{appearance_note}"
                )
            )

        anchor = blueprint.visual_anchor
        visual_dna = ", ".join(style_profile.get("visual_dna_pillars", []))
        shape_language = style_profile.get("shape_language", "")
        material_language = style_profile.get(
            "runtime_material_rule",
            style_profile.get("material_language", ""),
        )
        preserve = "; ".join(anchor.must_preserve)
        composition = "; ".join(anchor.composition_notes)
        relations = "; ".join(anchor.spatial_relations)

        return (
            "MINI UTOPIA UNIFIED HERO CLUSTER · IMAGE-TO-3D REFERENCE\n\n"
            "Render ONE complete inseparable fantasy Hero composition. "
            "The listed members are semantic parts of the SAME Hero and must read "
            "as one authored object, not as separate assets placed near each other.\n\n"
            f"Cluster concept: {cluster.concept_summary or anchor.concept_summary}.\n"
            f"Visual anchor concept: {anchor.concept_summary}.\n"
            + (f"Must preserve: {preserve}.\n" if preserve else "")
            + (f"Composition notes: {composition}.\n" if composition else "")
            + (f"Spatial relations: {relations}.\n" if relations else "")
            + (f"Visual DNA: {visual_dna}.\n" if visual_dna else "")
            + (f"Shape language: {shape_language}.\n" if shape_language else "")
            + (f"Material language: {material_language}.\n" if material_language else "")
            + "\nHERO MEMBERS — ALL MUST BE INTEGRATED INTO THE SAME SUBJECT\n"
            + "\n".join(member_lines)
            + "\n\nSTRICT COMPOSITION RULES\n"
            + "- Include every listed Hero member in one visually coherent, fused composition.\n"
            + "- Preserve support/contact relationships: carried structures must feel designed into the root body/surface, not floating as unrelated props.\n"
            + "- Preserve the original imaginative silhouette and composition language from the Visual Anchor.\n"
            + "- Show the complete Hero Cluster centered and VERY LARGE, filling about 92-96% of the frame while keeping the full silhouette visible.\n"
            + "- Use a clean three-quarter view that clearly exposes the whale body plus the integrated top/side structures.\n"
            + "- Favor a few bold, thick, readable toy-scale architectural masses over tiny micro-detail. Make the lighthouse, portal and station forms chunky enough to survive image-to-3D reconstruction.\n"
            + "- Reduce tiny flowers, thin rails, hairline trim and fragile ornament. Preserve their design intent using larger simplified shapes instead.\n"
            + "- Keep strong color-block separation between the whale body, carried station, lighthouse and portal so the 3D model can distinguish them.\n"
            + "- Plain soft neutral studio background with clear separation from the Hero.\n"
            + "- NO unrelated world scenery, distant islands, entrance plaza, generic roads, ambient lamps, background characters, labels, UI or text.\n"
            + "- This is ONE image-to-3D subject. Do not create detached pieces for later assembly.\n"
            + "- Keep Mini Utopia rounded storybook/toy stylization; avoid photorealism."
        )

    @staticmethod
    def _cluster_input_sha(
        *,
        reference_fingerprint: bytes,
        cluster: HeroCompositionCluster,
        member_ids: tuple[str, ...],
        appearance_by_id: dict[str, ObjectAppearanceSpec],
        provider_key: str,
        reference_mode: str,
        visual_anchor: dict,
    ) -> str:
        digest = hashlib.sha256()
        digest.update(b"hero-unified-cluster-v2\0")
        digest.update(provider_key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(reference_mode.encode("utf-8"))
        digest.update(b"\0")
        digest.update(reference_fingerprint)
        digest.update(
            json.dumps(
                {
                    "cluster": cluster.model_dump(mode="json"),
                    "member_ids": list(member_ids),
                    "appearances": {
                        element_id: appearance_by_id[element_id].model_dump(mode="json")
                        for element_id in member_ids
                        if element_id in appearance_by_id
                    },
                    "visual_anchor": visual_anchor,
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        )
        return digest.hexdigest()

    @staticmethod
    def _cluster_target_size(
        *,
        member_ids: tuple[str, ...],
        element_by_id: dict[str, WorldLayoutElement],
    ) -> tuple[float, float, float]:
        elements = [
            element_by_id[element_id]
            for element_id in member_ids
            if element_id in element_by_id
        ]
        if not elements:
            return (1.0, 1.0, 1.0)

        min_x = min(item.position.x - item.width / 2.0 for item in elements)
        max_x = max(item.position.x + item.width / 2.0 for item in elements)
        min_y = min(item.position.y - item.height / 2.0 for item in elements)
        max_y = max(item.position.y + item.height / 2.0 for item in elements)
        min_z = min(item.position.z - item.depth / 2.0 for item in elements)
        max_z = max(item.position.z + item.depth / 2.0 for item in elements)
        return (
            max(0.1, max_x - min_x),
            max(0.1, max_y - min_y),
            max(0.1, max_z - min_z),
        )

    @staticmethod
    def _suppress_baked_members(
        *,
        updated_by_id: dict,
        cluster: HeroCompositionCluster,
    ) -> None:
        for member in cluster.members:
            if member.role != "baked":
                continue
            render_object = updated_by_id.get(member.element_id)
            if render_object is not None:
                render_object.visible = False

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
    def _normalize_reference_image(
        image_bytes: bytes,
        size: int = 1024,
        max_fill: float = 0.88,
    ) -> bytes:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        max_object = int(size * max(0.5, min(0.98, max_fill)))
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
