from __future__ import annotations

from uuid import uuid4

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import AssetFile, now_utc
from studio.models.world import WorldBlueprint, WorldProfile
from studio.providers.base import ImageGenerationProvider
from studio.repositories.base import StudioRepository
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.storage.base import ObjectStorage


class WorldConceptService:
    def __init__(
        self,
        repository: StudioRepository,
        storage: ObjectStorage,
        prompt_service: WorldConceptPromptService,
        blueprint_service: WorldBlueprintService,
        image_provider: ImageGenerationProvider | None = None,
    ):
        self.repository = repository
        self.storage = storage
        self.prompt_service = prompt_service
        self.blueprint_service = blueprint_service
        self.image_provider = image_provider

    @property
    def is_available(self) -> bool:
        return self.image_provider is not None

    def plan_blueprint(
        self,
        *,
        location_asset_id: str,
        style_asset_id: str | None,
    ) -> WorldBlueprint:
        """Create the executable world before any beauty render exists."""
        world = self.repository.get_asset(location_asset_id)
        if world is None or world.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {location_asset_id}")

        profile = WorldProfile.model_validate(world.metadata.get("world_profile", {}))
        blueprint = self.blueprint_service.plan(
            location_asset_id=world.asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
        )
        world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
        world.metadata["world_pipeline"] = "blueprint_first_v1"
        world.metadata["world_blueprint_source"] = "creator_profile"
        # A rebuilt Blueprint invalidates any older beauty render. Keep the file
        # as archive history, but require the next preview to be rendered from
        # the new authoritative layout.
        for file_ref in world.files:
            if file_ref.role == "world_concept_approved":
                file_ref.role = "world_concept_archive"
        world.metadata.pop("world_concept_path", None)
        world.metadata.pop("world_preview_source", None)
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
        if not blueprint.layout_elements:
            raise ValueError(
                "World Preview requires a current Blueprint with layout elements."
            )
        blueprint_snapshot = blueprint.model_dump(mode="json")
        prompt = self.prompt_service.compose_from_blueprint(
            profile=profile,
            blueprint=blueprint,
            style_profile=style.metadata.get("style_profile", {}),
        )
        image_bytes = self.image_provider.generate(
            prompt=prompt,
            size=size,
            quality=quality,
        )

        preview_id = uuid4().hex[:12]
        path = self.storage.put_bytes(
            f"assets/{location_asset_id}/preview/blueprint_{preview_id}.png",
            image_bytes,
        )
        for file_ref in world.files:
            if file_ref.role == "world_concept_approved":
                file_ref.role = "world_concept_archive"
        file_ref = AssetFile(
            role="world_concept_approved",
            path=path,
            mime_type="image/png",
        )
        world.files.append(file_ref)
        world.metadata["world_concept_path"] = path
        world.metadata["world_preview_source"] = "blueprint"
        world.metadata["world_preview_last_prompt"] = prompt
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
        return file_ref

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
