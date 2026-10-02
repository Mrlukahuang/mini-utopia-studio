from __future__ import annotations

from uuid import uuid4

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import AssetFile
from studio.models.world import WorldProfile
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
        blueprint = self.blueprint_service.build(
            location_asset_id=world.asset_id,
            style_asset_id=style_asset_id,
            profile=profile,
            concept_path=selected.path,
            concept_direction=concept_direction,
        )
        world.metadata["world_blueprint"] = blueprint.model_dump(mode="json")
        self.repository.save_asset(world)
        return selected

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
