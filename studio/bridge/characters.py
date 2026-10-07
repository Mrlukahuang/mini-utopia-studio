from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import now_utc
from studio.models.character import CharacterProfile
from studio.repositories.base import StudioRepository


BRIDGE_CHARACTER_SCHEMA_VERSION = "1.0"


class BridgeCharacterContract(BaseModel):
    """Read contract consumed by Godot Creator.

    The profile is canonical CharacterProfile data. AvatarAppearance stays
    nested at profile.avatar so the transport never creates a second editable
    appearance object that could drift from the Character.
    """

    schema_version: str = BRIDGE_CHARACTER_SCHEMA_VERSION
    character_id: str
    display_name: str
    description: str = ""
    review_status: str
    revision: str
    profile: CharacterProfile


class BridgeCharacterUpdate(BaseModel):
    """Validated Godot -> Python Core Character update payload."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = BRIDGE_CHARACTER_SCHEMA_VERSION
    revision: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    profile: CharacterProfile

    @field_validator("display_name")
    @classmethod
    def _display_name_must_have_visible_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("display_name must contain visible text")
        return stripped


class CharacterWriteValidationError(ValueError):
    pass


class CharacterRevisionConflict(RuntimeError):
    def __init__(self, *, current_revision: str):
        super().__init__("Character revision conflict")
        self.current_revision = current_revision


class CharacterBridgeReader:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def list_characters(self) -> list[dict]:
        contracts: list[dict] = []
        for asset in self.repository.list_assets(AssetType.CHARACTER):
            if asset.status == ReviewStatus.ARCHIVED:
                continue
            contracts.append(self._contract(asset).model_dump(mode="json"))
        return contracts

    def get_character(self, character_id: str) -> dict | None:
        asset = self.repository.get_asset(character_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            return None
        return self._contract(asset).model_dump(mode="json")

    @staticmethod
    def _contract(asset) -> BridgeCharacterContract:
        profile = CharacterProfile.model_validate(
            asset.metadata.get("character_profile", {}) or {}
        )
        return BridgeCharacterContract(
            character_id=asset.asset_id,
            display_name=asset.display_name,
            description=asset.description,
            review_status=asset.status.value,
            revision=asset.updated_at.isoformat(),
            profile=profile,
        )


    def update_character(
        self,
        character_id: str,
        payload: dict,
    ) -> dict | None:
        """Update one canonical Character while preserving its stable ID.

        Identical replay is accepted even when the supplied revision is stale.
        A stale revision may not overwrite different current state.
        """

        asset = self.repository.get_asset(character_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            return None

        try:
            update = BridgeCharacterUpdate.model_validate(payload)
        except ValidationError as exc:
            raise CharacterWriteValidationError(
                "Character update payload failed validation."
            ) from exc

        current = self._contract(asset)
        current_profile_json = current.profile.model_dump(mode="json")
        desired_profile_json = update.profile.model_dump(mode="json")
        desired_name = update.display_name.strip()

        identical = (
            desired_name == current.display_name
            and update.description == current.description
            and desired_profile_json == current_profile_json
        )
        if identical:
            return current.model_dump(mode="json")

        if update.revision != current.revision:
            raise CharacterRevisionConflict(
                current_revision=current.revision,
            )

        asset.display_name = desired_name
        # Keep slug changes inside the existing service/domain convention
        # without routing through a second persistence abstraction.
        from studio.services.asset_service import slugify

        asset.slug = slugify(desired_name)
        asset.description = update.description
        asset.metadata["character_profile"] = desired_profile_json
        asset.updated_at = now_utc()
        self.repository.save_asset(asset)

        return self._contract(asset).model_dump(mode="json")
