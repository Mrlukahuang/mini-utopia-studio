from __future__ import annotations

from pydantic import BaseModel

from studio.core.enums import AssetType, ReviewStatus
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
