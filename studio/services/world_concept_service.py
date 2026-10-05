from __future__ import annotations

import hashlib

from collections.abc import Callable
from uuid import uuid4

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import AssetFile, now_utc
from studio.models.hero_composition import WorldHeroCompositionPlan
from studio.models.render import WorldAppearancePlan, WorldRenderSpec
from studio.models.world import WorldBlueprint, WorldProfile, WorldScenePlan
from studio.providers.base import ImageGenerationProvider
from studio.repositories.base import StudioRepository
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.services.world_appearance_service import (
    WorldAppearancePlanningError,
    WorldAppearanceService,
)
from studio.services.world_geometry_compiler_service import WorldGeometryCompilerService
from studio.services.world_hero_asset_service import WorldHeroAssetService
from studio.services.world_hero_composition_service import WorldHeroCompositionService
from studio.storage.base import ObjectStorage


WorldBuildProgressCallback = Callable[[str, str, float], None]


class WorldConceptService:
    def __init__(
        self,
        repository: StudioRepository,
        storage: ObjectStorage,
        prompt_service: WorldConceptPromptService,
        blueprint_service: WorldBlueprintService,
        image_provider: ImageGenerationProvider | None = None,
        appearance_service: WorldAppearanceService | None = None,
        geometry_compiler: WorldGeometryCompilerService | None = None,
        hero_asset_service: WorldHeroAssetService | None = None,
        hero_composition_service: WorldHeroCompositionService | None = None,
    ):
        self.repository = repository
        self.storage = storage
        self.prompt_service = prompt_service
        self.blueprint_service = blueprint_service
        self.image_provider = image_provider
        self.appearance_service = appearance_service
        self.geometry_compiler = geometry_compiler
        self.hero_asset_service = hero_asset_service
        self.hero_composition_service = hero_composition_service

    @property
    def is_available(self) -> bool:
        return self.image_provider is not None

    def plan_blueprint(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
        scene_plan: WorldScenePlan | None = None,
    ) -> WorldBlueprint:
        """Create executable runtime truth from the shared semantic Scene Plan."""
        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        profile = WorldProfile.model_validate(world.metadata.get("world_profile", {}))
        if scene_plan is None:
            stored_plan = world.metadata.get("world_scene_plan")
            if stored_plan:
                scene_plan = WorldScenePlan.model_validate(stored_plan)

        if scene_plan is not None:
            blueprint = self.blueprint_service.plan_from_scene_plan(
                location_asset_id=world.asset_id,
                style_asset_id=style_asset_id,
                profile=profile,
                scene_plan=scene_plan,
            )
            scene_fingerprint = self._fingerprint(scene_plan.model_dump_json())
            profile_fingerprint = self._fingerprint(profile.model_dump_json())
            world.metadata["world_scene_plan"] = scene_plan.model_dump(mode="json")
            world.metadata["world_scene_plan_version"] = scene_plan.schema_version
            world.metadata["world_scene_plan_fingerprint"] = scene_fingerprint
            world.metadata["world_blueprint_scene_plan_fingerprint"] = scene_fingerprint
            world.metadata["world_blueprint_profile_fingerprint"] = profile_fingerprint
            world.metadata["world_blueprint_source"] = (
                f"scene_plan:{scene_plan.source_mode}"
            )
        else:
            # Compatibility fallback for Worlds created before Scene Plan v0.1.
            blueprint = self.blueprint_service.plan(
                location_asset_id=world.asset_id,
                style_asset_id=style_asset_id,
                profile=profile,
            )
            world.metadata["world_blueprint_source"] = "legacy_creator_profile"

        world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
        if scene_plan is not None:
            self._ensure_hero_composition_plan(
                world=world,
                profile=profile,
                scene_plan=scene_plan,
                blueprint=blueprint,
            )
        self._refresh_render_pipeline(
            world=world,
            profile=profile,
            blueprint=blueprint,
            style_asset_id=style_asset_id,
        )
        world.metadata["world_pipeline"] = "blueprint_first_v1"
        # A rebuilt Blueprint invalidates any older beauty render. Keep the file
        # as archive history, but require the next preview to be rendered from
        # the new authoritative layout.
        for file_ref in world.files:
            if file_ref.role == "world_concept_approved":
                file_ref.role = "world_concept_archive"
            elif file_ref.role == "world_preview":
                file_ref.role = "world_preview_archive"
        world.metadata.pop("world_concept_path", None)
        world.metadata.pop("world_preview_path", None)
        world.metadata.pop("world_preview_source", None)
        world.metadata.pop("world_preview_last_prompt", None)
        world.metadata.pop("world_concept_match_reviewed", None)
        world.metadata.pop("world_concept_match_reviewed_at", None)
        world.metadata["world_concept_match_history"] = []
        world.status = ReviewStatus.APPROVED
        world.updated_at = now_utc()
        self.repository.save_asset(world)

        persisted = self.repository.get_asset(world.asset_id)
        if persisted is None:
            raise RuntimeError("World disappeared after Blueprint planning.")
        persisted_blueprint = persisted.metadata.get("world_blueprint") or {}
        if not persisted_blueprint.get("layout_elements"):
            raise RuntimeError("Blueprint planning did not persist layout elements.")
        return blueprint

    def render_blueprint_preview(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str,
        size: str = "1536x1024",
        quality: str = "medium",
        progress_callback: WorldBuildProgressCallback | None = None,
    ) -> AssetFile:
        """Render one visual preview from Blueprint without changing Blueprint data."""
        if self.image_provider is None:
            raise RuntimeError("World image generation is not configured.")

        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")
        raw_blueprint = world.metadata.get("world_blueprint")
        if not raw_blueprint:
            raise ValueError("World does not have a Blueprint to render.")

        style = self.repository.get_asset(style_asset_id)
        if style is None or style.asset_type != AssetType.STYLE:
            raise ValueError(f"Style not found: {style_asset_id}")

        profile = WorldProfile.model_validate(world.metadata.get("world_profile", {}))
        blueprint = WorldBlueprint.model_validate(raw_blueprint)
        if world.metadata.get("world_pipeline") != "blueprint_first_v1":
            raise ValueError(
                "World Preview requires a Blueprint-first plan. Rebuild the Blueprint first."
            )
        raw_scene_plan = world.metadata.get("world_scene_plan")
        if not raw_scene_plan:
            raise ValueError(
                "World Preview requires a Scene Plan. Rebuild this World with the current planner."
            )
        current_scene = WorldScenePlan.model_validate(raw_scene_plan)
        current_scene_fingerprint = self._fingerprint(current_scene.model_dump_json())
        current_profile_fingerprint = self._fingerprint(profile.model_dump_json())
        if (
            world.metadata.get("world_blueprint_scene_plan_fingerprint")
            != current_scene_fingerprint
            or world.metadata.get("world_blueprint_profile_fingerprint")
            != current_profile_fingerprint
        ):
            raise ValueError(
                "World Preview requires a Blueprint rebuilt from the current Scene Plan and Profile."
            )
        if not blueprint.layout_elements:
            raise ValueError(
                "World Preview requires a current Blueprint with layout elements."
            )
        blueprint_snapshot = blueprint.model_dump(mode="json")
        self._ensure_hero_composition_plan(
            world=world,
            profile=profile,
            scene_plan=current_scene,
            blueprint=blueprint,
        )
        featured_names = "、".join(
            element.name for element in blueprint.layout_elements[:3]
        )
        self._report_progress(
            progress_callback,
            "blueprint",
            (
                f"🗺️ Blueprint 已锁定 · {len(blueprint.layout_elements)} 个世界元素"
                + (f" · {featured_names}" if featured_names else "")
            ),
            0.06,
        )
        self._refresh_render_pipeline(
            world=world,
            profile=profile,
            blueprint=blueprint,
            style_asset_id=style_asset_id,
            progress_callback=progress_callback,
            force_appearance_regeneration=True,
            strict_appearance=True,
            repair_weak_heroes=True,
        )
        raw_appearance = world.metadata.get("world_appearance_plan")
        appearance_plan = (
            WorldAppearancePlan.model_validate(raw_appearance)
            if raw_appearance
            else None
        )
        self._report_progress(
            progress_callback,
            "art_direction",
            "🎨 正在把 Blueprint + 外观设计整理成统一的 Mini Utopia 美术指导…",
            0.32,
        )
        prompt = self.prompt_service.compose_from_blueprint(
            profile=profile,
            blueprint=blueprint,
            style_profile=style.metadata.get("style_profile", {}),
            appearance_plan=appearance_plan,
        )
        self._report_progress(
            progress_callback,
            "preview",
            "🖼️ 正在生成 World Preview · 把这个世界先画出来…",
            0.42,
        )
        image_bytes = self.image_provider.generate(
            prompt=prompt,
            size=size,
            quality=quality,
        )

        self._report_progress(
            progress_callback,
            "preview_ready",
            "✨ World Preview 已完成 · 现在开始让 Vision 对照画面校正 3D 外观…",
            0.66,
        )

        preview_id = uuid4().hex[:12]
        path = self.storage.put_bytes(
            f"assets/{location_asset_id}/preview/blueprint_{preview_id}.png",
            image_bytes,
        )
        for file_ref in world.files:
            if file_ref.role == "world_preview":
                file_ref.role = "world_preview_archive"
        file_ref = AssetFile(
            role="world_preview",
            path=path,
            mime_type="image/png",
        )
        world.files.append(file_ref)
        world.metadata["world_preview_path"] = path
        world.metadata["world_preview_source"] = "blueprint"
        world.metadata["world_preview_last_prompt"] = prompt
        self._refresh_render_pipeline(
            world=world,
            profile=profile,
            blueprint=blueprint,
            style_asset_id=style_asset_id,
            preview_image_bytes=image_bytes,
            preview_mime_type="image/png",
            progress_callback=progress_callback,
            strict_appearance=True,
            repair_weak_heroes=True,
        )
        self._report_progress(
            progress_callback,
            "persist",
            "💾 正在保存最终 AppearancePlan + RenderSpec…",
            0.95,
        )
        world.metadata["world_pipeline"] = "blueprint_first_v1"
        world.status = ReviewStatus.APPROVED
        world.updated_at = now_utc()

        # Preview generation is intentionally not allowed to mutate the source of truth.
        if world.metadata.get("world_blueprint") != blueprint_snapshot:
            raise RuntimeError("World Preview render attempted to mutate the Blueprint.")
        self.repository.save_asset(world)

        persisted = self.repository.get_asset(world.asset_id)
        if persisted is None:
            raise RuntimeError("World disappeared after Preview render.")
        if persisted.metadata.get("world_blueprint") != blueprint_snapshot:
            raise RuntimeError("World Blueprint changed while rendering Preview.")
        self._report_progress(
            progress_callback,
            "ready",
            "🌟 世界准备好了 · Preview 与 Three.js RenderSpec 已同步完成！",
            1.0,
        )
        return file_ref

    def _refresh_render_pipeline(
        self,
        *,
        world,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        style_asset_id: str | None,
        preview_image_bytes: bytes | None = None,
        preview_mime_type: str = "image/png",
        progress_callback: WorldBuildProgressCallback | None = None,
        force_appearance_regeneration: bool = False,
        strict_appearance: bool = False,
        repair_weak_heroes: bool = False,
    ) -> None:
        """Refresh appearance/render data without changing Blueprint world logic."""
        if self.appearance_service is None or self.geometry_compiler is None:
            return

        style_profile: dict = {}
        if style_asset_id:
            style = self.repository.get_asset(style_asset_id)
            if style is not None:
                style_profile = style.metadata.get("style_profile", {}) or {}

        blueprint_fingerprint = self._fingerprint(blueprint.model_dump_json())
        raw_plan = world.metadata.get("world_appearance_plan")
        can_reuse_plan = bool(
            not force_appearance_regeneration
            and raw_plan
            and world.metadata.get("world_render_blueprint_fingerprint")
            == blueprint_fingerprint
        )
        appearance_fallback_source = ""

        def generate_fresh_appearance() -> WorldAppearancePlan:
            nonlocal appearance_fallback_source
            try:
                result = self.appearance_service.plan_from_blueprint(
                    profile=profile,
                    blueprint=blueprint,
                    style_profile=style_profile,
                    strict_provider=strict_appearance,
                    repair_weak_heroes=repair_weak_heroes,
                )
            except WorldAppearancePlanningError as exc:
                if not strict_appearance:
                    raise

                # A transient GPT timeout must not throw away a previously valid
                # world. Prefer the last saved plan because it preserves object
                # identity and detail better than the deterministic fallback.
                saved_plan = None
                if raw_plan:
                    try:
                        saved_plan = WorldAppearancePlan.model_validate(raw_plan)
                    except Exception:
                        saved_plan = None

                if saved_plan is not None:
                    result = saved_plan
                    appearance_fallback_source = "saved_plan_gpt_fallback"
                    fallback_message = (
                        "⚠️ GPT AppearancePlan 暂时不可用 · 沿用已保存外观，继续生成 Preview…"
                    )
                else:
                    result = self.appearance_service.fallback_from_blueprint(
                        profile=profile,
                        blueprint=blueprint,
                    )
                    appearance_fallback_source = "deterministic_gpt_fallback"
                    fallback_message = (
                        "⚠️ GPT AppearancePlan 暂时不可用 · 使用 Blueprint 安全外观继续构建…"
                    )

                world.metadata["world_appearance_generation_status"] = "fallback"
                world.metadata["world_appearance_generation_error"] = str(exc)
                world.metadata["world_appearance_generation_fallback"] = (
                    appearance_fallback_source
                )
                self._report_progress(
                    progress_callback,
                    "appearance_fallback",
                    fallback_message,
                    0.22 if not preview_image_bytes else 0.72,
                )
                return result

            appearance_fallback_source = ""
            world.metadata["world_appearance_generation_status"] = "success"
            world.metadata.pop("world_appearance_generation_error", None)
            world.metadata.pop("world_appearance_generation_fallback", None)
            return result

        if can_reuse_plan:
            self._report_progress(
                progress_callback,
                "appearance",
                "🧠 正在检查已经设计好的世界物件外观…",
                0.14 if not preview_image_bytes else 0.69,
            )
            try:
                appearance = WorldAppearancePlan.model_validate(raw_plan)
            except Exception:
                self._report_progress(
                    progress_callback,
                    "appearance",
                    "✨ 外观设计需要更新 · 正在重新设计各个世界物件…",
                    0.18 if not preview_image_bytes else 0.71,
                )
                appearance = generate_fresh_appearance()
        else:
            self._report_progress(
                progress_callback,
                "appearance",
                "✨ 正在根据 Blueprint 设计每个世界物件的形状、部件与材质…",
                0.16,
            )
            appearance = generate_fresh_appearance()

        if not preview_image_bytes:
            diagnostics = self.appearance_service.summarize_plan(
                blueprint=blueprint,
                plan=appearance,
            )
            world.metadata["world_appearance_diagnostics"] = diagnostics
            hero_parts = [
                f"{item['name']}:{item['part_count']} parts"
                for item in diagnostics["objects"]
                if item["geometry_role"] == "organic"
            ]
            detail = " · ".join(hero_parts[:3])
            self._report_progress(
                progress_callback,
                "appearance_ready",
                (
                    f"🧩 Object AppearancePlan 已完成 · {len(appearance.objects)} 个物件"
                    + (f" · {detail}" if detail else "")
                ),
                0.27,
            )

        if preview_image_bytes:
            self._report_progress(
                progress_callback,
                "vision",
                "👁️ 正在让 Vision 对照 Preview 校正轮廓、部件、颜色角色和材质…",
                0.74,
            )
            try:
                appearance = self.appearance_service.refine_from_preview(
                    profile=profile,
                    blueprint=blueprint,
                    style_profile=style_profile,
                    base_plan=appearance,
                    image_bytes=preview_image_bytes,
                    mime_type=preview_mime_type,
                    strict_provider=strict_appearance,
                    repair_weak_heroes=repair_weak_heroes,
                )
            except Exception as exc:
                # Preview Vision is a quality-enhancement pass. By this point
                # Blueprint, the fresh GPT AppearancePlan and the rendered
                # Preview already exist, so a transient image-analysis timeout
                # must not prevent Geometry/Hero generation or entering World.
                world.metadata["world_appearance_source"] = (
                    "blueprint+gpt_vision_fallback"
                )
                world.metadata["world_preview_vision_status"] = "fallback"
                world.metadata["world_preview_vision_error"] = str(exc)
                world.metadata["world_appearance_diagnostics"] = (
                    self.appearance_service.summarize_plan(
                        blueprint=blueprint,
                        plan=appearance,
                    )
                )
                self._report_progress(
                    progress_callback,
                    "vision_fallback",
                    (
                        "⚠️ Vision 校正暂时不可用 · 保留已完成的 AppearancePlan，"
                        "继续构建 3D 世界…"
                    ),
                    0.78,
                )
            else:
                world.metadata["world_appearance_source"] = "blueprint+preview_vision"
                world.metadata["world_preview_vision_status"] = "success"
                world.metadata.pop("world_preview_vision_error", None)
                world.metadata["world_appearance_diagnostics"] = (
                    self.appearance_service.summarize_plan(
                        blueprint=blueprint,
                        plan=appearance,
                    )
                )
        else:
            world.metadata["world_appearance_source"] = (
                f"blueprint+{appearance_fallback_source}"
                if appearance_fallback_source
                else (
                    "blueprint+gpt_fresh"
                    if force_appearance_regeneration
                    else "blueprint+creator_prompt"
                )
            )

        if preview_image_bytes:
            self._report_progress(
                progress_callback,
                "geometry",
                "🧱 正在把最终外观说明编译成 Three.js RenderSpec…",
                0.88,
            )
        render_spec = self.geometry_compiler.compile(
            profile=profile,
            blueprint=blueprint,
            appearance=appearance,
            style_profile=style_profile,
        )

        if (
            preview_image_bytes
            and self.hero_asset_service is not None
            and self.hero_asset_service.is_available
        ):
            composition_plan = None
            raw_composition = world.metadata.get("world_hero_composition_plan")
            if raw_composition:
                try:
                    composition_plan = WorldHeroCompositionPlan.model_validate(
                        raw_composition
                    )
                except Exception:
                    composition_plan = None

            self._report_progress(
                progress_callback,
                "hero_asset",
                (
                    "🐋 正在把完整 Hero Cluster 转成一个统一 3D GLB…"
                    if composition_plan and composition_plan.clusters
                    else "🐋 正在把主要 Hero 从 Preview 转成真正的 3D GLB…"
                ),
                0.91,
            )
            render_spec, hero_builds, hero_cache = (
                self.hero_asset_service.enrich_render_spec(
                    location_asset_id=world.asset_id,
                    blueprint=blueprint,
                    appearance=appearance,
                    render_spec=render_spec,
                    preview_image_bytes=preview_image_bytes,
                    preview_mime_type=preview_mime_type,
                    profile=profile,
                    style_profile=style_profile,
                    existing_assets=world.metadata.get("world_hero_assets", {}),
                    composition_plan=composition_plan,
                )
            )
            world.metadata["world_hero_assets"] = hero_cache
            world.metadata["world_hero_asset_diagnostics"] = [
                {
                    "element_id": item.element_id,
                    "name": item.name,
                    "status": item.status,
                    "asset_path": item.asset_path,
                    "model": item.model,
                    "bytes": item.bytes,
                    "reference_mode": item.reference_mode,
                    "usage": item.usage,
                    "message": item.message,
                    "cluster_id": item.cluster_id,
                    "member_element_ids": list(item.member_element_ids),
                    "target_size": (
                        list(item.target_size)
                        if item.target_size is not None
                        else None
                    ),
                }
                for item in hero_builds
            ]

        world.metadata["world_appearance_plan"] = appearance.model_dump(mode="json")
        world.metadata["world_appearance_schema_version"] = appearance.schema_version
        world.metadata["world_render_spec"] = render_spec.model_dump(mode="json")
        world.metadata["world_render_schema_version"] = render_spec.schema_version
        world.metadata["world_render_blueprint_fingerprint"] = blueprint_fingerprint
        world.metadata["world_render_diagnostics"] = {
            "object_count": len(render_spec.objects),
            "objects": [
                {
                    "element_id": item.element_id,
                    "name": item.name,
                    "node_count": len(item.nodes),
                    "node_ids": [node.node_id for node in item.nodes],
                }
                for item in render_spec.objects
            ],
        }

    def _ensure_hero_composition_plan(
        self,
        *,
        world,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan | None:
        if self.hero_composition_service is None:
            return None

        fingerprint = self._fingerprint(
            "|".join(
                [
                    profile.source_description,
                    scene_plan.model_dump_json(),
                    blueprint.visual_anchor.model_dump_json(),
                    ",".join(
                        element.element_id for element in blueprint.layout_elements
                    ),
                ]
            )
        )
        raw = world.metadata.get("world_hero_composition_plan")
        if raw and world.metadata.get("world_hero_composition_fingerprint") == fingerprint:
            try:
                return WorldHeroCompositionPlan.model_validate(raw)
            except Exception:
                pass

        plan = self.hero_composition_service.resolve(
            profile=profile,
            scene_plan=scene_plan,
            blueprint=blueprint,
        )
        world.metadata["world_hero_composition_plan"] = plan.model_dump(mode="json")
        world.metadata["world_hero_composition_version"] = plan.schema_version
        world.metadata["world_hero_composition_source"] = plan.source
        world.metadata["world_hero_composition_fingerprint"] = fingerprint
        return plan

    @staticmethod
    def _report_progress(
        callback: WorldBuildProgressCallback | None,
        stage: str,
        message: str,
        progress: float,
    ) -> None:
        if callback is None:
            return
        callback(stage, message, max(0.0, min(1.0, progress)))

    def attach_manual_hero_glb(
        self,
        *,
        location_asset_id: str,
        element_id: str,
        payload: bytes,
    ):
        if self.hero_asset_service is None:
            raise RuntimeError("Hero Asset service is not configured.")

        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        raw_blueprint = world.metadata.get("world_blueprint")
        raw_render_spec = world.metadata.get("world_render_spec")
        if not raw_blueprint or not raw_render_spec:
            raise ValueError(
                "Manual Hero GLB requires an existing Blueprint and RenderSpec."
            )

        blueprint = WorldBlueprint.model_validate(raw_blueprint)
        render_spec = WorldRenderSpec.model_validate(raw_render_spec)
        updated, build, record = self.hero_asset_service.attach_existing_glb(
            location_asset_id=location_asset_id,
            blueprint=blueprint,
            render_spec=render_spec,
            element_id=element_id,
            payload=payload,
        )

        world.metadata["world_render_spec"] = updated.model_dump(mode="json")
        cache = dict(world.metadata.get("world_hero_assets", {}) or {})
        cache[element_id] = record
        world.metadata["world_hero_assets"] = cache
        diagnostics = [
            item
            for item in (
                world.metadata.get("world_hero_asset_diagnostics", []) or []
            )
            if item.get("element_id") != element_id
        ]
        diagnostics.append(
            {
                "element_id": build.element_id,
                "name": build.name,
                "status": build.status,
                "asset_path": build.asset_path,
                "model": build.model,
                "bytes": build.bytes,
                "message": build.message,
            }
        )
        world.metadata["world_hero_asset_diagnostics"] = diagnostics
        world.metadata["world_render_diagnostics"] = {
            "object_count": len(updated.objects),
            "objects": [
                {
                    "element_id": item.element_id,
                    "name": item.name,
                    "node_count": len(item.nodes),
                    "node_ids": [node.node_id for node in item.nodes],
                }
                for item in updated.objects
            ],
        }
        world.updated_at = now_utc()
        self.repository.save_asset(world)
        return build

    def current_render_spec(self, location_asset_id: str) -> WorldRenderSpec | None:
        world = self.repository.get_asset(location_asset_id)
        if world is None:
            return None
        raw = world.metadata.get("world_render_spec")
        if not raw:
            return None
        try:
            return WorldRenderSpec.model_validate(raw)
        except Exception:
            return None

    @staticmethod
    def _fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def current_preview(self, location_asset_id: str) -> AssetFile | None:
        """Return the current Blueprint-first beauty preview, if one exists."""
        world = self.repository.get_asset(location_asset_id)
        if world is None:
            return None
        for file_ref in reversed(world.files):
            if file_ref.role == "world_preview":
                return file_ref
        metadata_path = world.metadata.get("world_preview_path")
        if metadata_path:
            return AssetFile(
                role="world_preview",
                path=metadata_path,
                mime_type="image/png",
            )
        return None

    def generate_candidate(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str,
        direction: str,
        size: str = "1536x1024",
        quality: str = "medium",
    ) -> AssetFile:
        if self.image_provider is None:
            raise RuntimeError("World image generation is not configured.")

        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        style = self.repository.get_asset(style_asset_id)
        if style is None or style.asset_type != AssetType.STYLE:
            raise ValueError(f"Style not found: {style_asset_id}")

        profile = WorldProfile.model_validate(world.metadata.get("world_profile", {}))
        prompt = self.prompt_service.compose(
            profile=profile,
            style_profile=style.metadata.get("style_profile", {}),
            direction=direction,
        )
        image_bytes = self.image_provider.generate(
            prompt=prompt,
            size=size,
            quality=quality,
        )

        candidate_id = uuid4().hex[:12]
        path = self.storage.put_bytes(
            f"assets/{location_asset_id}/concept/candidates/{direction}_{candidate_id}.png",
            image_bytes,
        )
        file_ref = AssetFile(
            role="world_concept_candidate",
            path=path,
            mime_type="image/png",
        )
        world.files.append(file_ref)
        world.status = ReviewStatus.NEEDS_REVIEW
        world.metadata["world_concept_last_prompt"] = prompt
        world.metadata["world_concept_last_direction"] = direction
        world.updated_at = now_utc()
        self.repository.save_asset(world)
        return file_ref

    def approve_candidate(
        self,
        *,
        location_asset_id: str,
        candidate_path: str,
        style_asset_id: str,
    ) -> AssetFile:
        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        selected = None
        for file_ref in world.files:
            if file_ref.role == "world_concept_approved":
                file_ref.role = "world_concept_archive"
            if (
                file_ref.path == candidate_path
                and file_ref.role == "world_concept_candidate"
            ):
                selected = file_ref

        if selected is None:
            raise ValueError("World concept candidate not found.")

        selected.role = "world_concept_approved"
        world.status = ReviewStatus.APPROVED
        world.version += 1
        world.metadata["world_concept_path"] = selected.path

        profile = WorldProfile.model_validate(world.metadata.get("world_profile", {}))
        concept_direction = selected.path.rsplit("/", 1)[-1].split("_", 1)[0]
        concept_image_bytes = self.storage.get_bytes(selected.path)
        blueprint = self.blueprint_service.build(
            location_asset_id=world.asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            concept_path=selected.path,
            concept_direction=concept_direction,
            concept_image_bytes=concept_image_bytes,
            concept_mime_type=selected.mime_type or "image/png",
        )
        world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
        world.metadata["world_pipeline"] = "legacy_concept_v1"
        world.metadata["world_blueprint_source"] = "approved_concept"
        world.metadata.pop("world_blueprint_scene_plan_fingerprint", None)
        world.metadata.pop("world_blueprint_profile_fingerprint", None)
        world.updated_at = now_utc()
        self.repository.save_asset(world)

        persisted = self.repository.get_asset(world.asset_id)
        if persisted is None:
            raise RuntimeError("Approved World disappeared after persistence write.")
        if persisted.metadata.get("world_concept_path") != selected.path:
            raise RuntimeError("Approved World Concept was not durably persisted.")
        if not persisted.metadata.get("world_blueprint"):
            raise RuntimeError("World Blueprint was not durably persisted.")

        return selected

    def rebuild_blueprint_from_current_concept(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
    ):
        """Upgrade a legacy approved World using its existing Concept image.

        This does not generate new Concept Art. It rebuilds the executable
        Blueprint with the current compiler so older worlds gain visual anchors,
        layout elements, synchronized zones, paths and cameras.
        """
        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        concept = self.current_concept(location_asset_id)
        if concept is None:
            raise ValueError("World does not have an approved Concept image.")

        profile = WorldProfile.model_validate(world.metadata.get("world_profile", {}))
        concept_direction = (
            world.metadata.get("world_concept_last_direction")
            or concept.path.rsplit("/", 1)[-1].split("_", 1)[0]
        )
        concept_image_bytes = self.storage.get_bytes(concept.path)
        blueprint = self.blueprint_service.build(
            location_asset_id=world.asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            concept_path=concept.path,
            concept_direction=concept_direction,
            concept_image_bytes=concept_image_bytes,
            concept_mime_type=concept.mime_type or "image/png",
        )

        world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
        world.metadata["world_pipeline"] = "legacy_concept_v1"
        world.metadata["world_blueprint_source"] = "legacy_approved_concept"
        world.metadata.pop("world_blueprint_scene_plan_fingerprint", None)
        world.metadata.pop("world_blueprint_profile_fingerprint", None)
        world.metadata["world_concept_match_reviewed"] = False
        world.metadata.pop("world_concept_match_reviewed_at", None)
        world.metadata["world_concept_match_history"] = []
        world.metadata["world_blueprint_legacy_upgraded"] = True
        world.updated_at = now_utc()
        self.repository.save_asset(world)

        persisted = self.repository.get_asset(world.asset_id)
        if persisted is None:
            raise RuntimeError("World disappeared after Blueprint upgrade.")
        persisted_blueprint = persisted.metadata.get("world_blueprint") or {}
        if not persisted_blueprint.get("layout_elements"):
            raise RuntimeError("Blueprint upgrade did not persist layout elements.")
        return blueprint

    def current_concept(self, location_asset_id: str) -> AssetFile | None:
        world = self.repository.get_asset(location_asset_id)
        if world is None:
            return None
        for file_ref in reversed(world.files):
            if file_ref.role == "world_concept_approved":
                return file_ref
        metadata_path = world.metadata.get("world_concept_path")
        if metadata_path:
            return AssetFile(
                role="world_concept_approved",
                path=metadata_path,
                mime_type="image/png",
            )
        return None
