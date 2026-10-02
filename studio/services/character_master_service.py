from __future__ import annotations

from uuid import uuid4

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import AssetFile
from studio.models.character import CharacterProfile
from studio.providers.base import ImageGenerationProvider
from studio.repositories.base import StudioRepository
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.storage.base import ObjectStorage


class CharacterMasterService:
    def __init__(
        self,
        repository: StudioRepository,
        storage: ObjectStorage,
        prompt_service: CharacterMasterPromptService,
        image_provider: ImageGenerationProvider | None = None,
    ):
        self.repository = repository
        self.storage = storage
        self.prompt_service = prompt_service
        self.image_provider = image_provider

    @property
    def is_available(self) -> bool:
        return self.image_provider is not None

    def compose_prompt(self, *, character_asset_id: str, style_asset_id: str) -> str:
        character = self.repository.get_asset(character_asset_id)
        if character is None or character.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {character_asset_id}")

        style = self.repository.get_asset(style_asset_id)
        if style is None or style.asset_type != AssetType.STYLE:
            raise ValueError(f"Style not found: {style_asset_id}")

        profile = CharacterProfile.model_validate(
            character.metadata.get("character_profile", {})
        )
        wearable_descriptions: dict[str, str] = {}
        for slot, wearable_id in {
            "top": profile.wearables.top_id,
            "bottom": profile.wearables.bottom_id,
            "shoes": profile.wearables.shoes_id,
            "hat": profile.wearables.hat_id,
        }.items():
            if not wearable_id:
                continue
            wearable = self.repository.get_asset(wearable_id)
            if wearable is not None and wearable.asset_type == AssetType.WEARABLE:
                wearable_descriptions[slot] = (
                    f"{wearable.display_name}. {wearable.description}".strip()
                )

        return self.prompt_service.compose(
            name=character.display_name,
            profile=profile,
            style_profile=style.metadata.get("style_profile", {}),
            wearable_descriptions=wearable_descriptions,
        )

    def generate_candidate(
        self,
        *,
        character_asset_id: str,
        style_asset_id: str,
        size: str = "1536x1024",
        quality: str = "medium",
    ) -> AssetFile:
        if self.image_provider is None:
            raise RuntimeError("Character image generation is not configured.")

        character = self.repository.get_asset(character_asset_id)
        if character is None or character.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {character_asset_id}")

        prompt = self.compose_prompt(
            character_asset_id=character_asset_id,
            style_asset_id=style_asset_id,
        )
        image_bytes = self.image_provider.generate(
            prompt=prompt,
            size=size,
            quality=quality,
        )

        candidate_id = uuid4().hex[:12]
        relative_path = (
            f"assets/{character_asset_id}/master/candidates/"
            f"{candidate_id}.png"
        )
        stored_path = self.storage.put_bytes(relative_path, image_bytes)

        file_ref = AssetFile(
            role="character_master_candidate",
            path=stored_path,
            mime_type="image/png",
        )
        character.files.append(file_ref)
        character.status = ReviewStatus.NEEDS_REVIEW
        character.metadata["character_master_last_prompt"] = prompt
        character.metadata["character_master_last_size"] = size
        character.metadata["character_master_last_quality"] = quality
        self.repository.save_asset(character)
        return file_ref

    def approve_candidate(
        self,
        *,
        character_asset_id: str,
        candidate_path: str,
    ) -> AssetFile:
        character = self.repository.get_asset(character_asset_id)
        if character is None or character.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {character_asset_id}")

        selected = None
        for file_ref in character.files:
            if file_ref.role == "character_master":
                file_ref.role = "character_master_archive"
            if (
                file_ref.path == candidate_path
                and file_ref.role == "character_master_candidate"
            ):
                selected = file_ref

        if selected is None:
            raise ValueError("Character Master candidate not found.")

        selected.role = "character_master"
        character.status = ReviewStatus.APPROVED
        character.version += 1
        character.metadata["character_master_path"] = selected.path
        self.repository.save_asset(character)
        return selected

    def current_master(self, character_asset_id: str) -> AssetFile | None:
        character = self.repository.get_asset(character_asset_id)
        if character is None:
            return None
        for file_ref in reversed(character.files):
            if file_ref.role == "character_master":
                return file_ref

        # Backward-compatibility fallback for older Character records where
        # the approved master path was persisted in metadata but the file-role
        # list is incomplete.
        metadata_path = character.metadata.get("character_master_path")
        if metadata_path:
            return AssetFile(
                role="character_master",
                path=metadata_path,
                mime_type="image/png",
            )
        return None
