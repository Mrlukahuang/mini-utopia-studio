from __future__ import annotations
import re
from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.repositories.base import StudioRepository


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip()).strip("-").lower()
    return value or "asset"


class AssetService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def create_character(self, *, name: str, description: str, profile: CharacterProfile) -> Asset:
        asset = Asset.create(
            AssetType.CHARACTER,
            display_name=name,
            slug=slugify(name),
            description=description,
            metadata={"character_profile": profile.model_dump(mode="json")},
        )
        self.repository.save_asset(asset)
        return asset
