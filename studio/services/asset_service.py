from __future__ import annotations
import re
from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.world import WorldProfile
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

    def update_character(
        self,
        *,
        asset_id: str,
        name: str,
        description: str,
        profile: CharacterProfile,
    ) -> Asset:
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {asset_id}")
        asset.display_name = name
        asset.slug = slugify(name)
        asset.description = description
        asset.metadata["character_profile"] = profile.model_dump(mode="json")
        self.repository.save_asset(asset)
        return asset

    def create_world(
        self,
        *,
        name: str,
        description: str,
        profile: WorldProfile,
    ) -> Asset:
        asset = Asset.create(
            AssetType.LOCATION,
            display_name=name,
            slug=slugify(name),
            description=description,
            metadata={
                "world_profile": profile.model_dump(mode="json"),
                "world_creation_complete": False,
            },
        )
        self.repository.save_asset(asset)
        return asset

    def update_world(
        self,
        *,
        asset_id: str,
        name: str,
        description: str,
        profile: WorldProfile,
    ) -> Asset:
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {asset_id}")
        asset.display_name = name
        asset.slug = slugify(name)
        asset.description = description
        asset.metadata["world_profile"] = profile.model_dump(mode="json")
        self.repository.save_asset(asset)
        return asset

    def complete_world(self, asset_id: str) -> Asset:
        """Publish a World to the Library after the creator explicitly finishes it."""
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {asset_id}")
        asset.metadata["world_creation_complete"] = True
        self.repository.save_asset(asset)
        return asset

    def archive_world(self, asset_id: str) -> Asset:
        """Soft-delete a World while preserving Story/Asset references."""
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {asset_id}")
        asset.status = ReviewStatus.ARCHIVED
        self.repository.save_asset(asset)
        return asset

    @staticmethod
    def is_world_library_visible(asset: Asset) -> bool:
        """Hide unfinished new drafts while keeping pre-metadata legacy Worlds visible."""
        return bool(
            asset.asset_type == AssetType.LOCATION
            and asset.status != ReviewStatus.ARCHIVED
            and "world_profile" in asset.metadata
            and asset.metadata.get("world_creation_complete", True)
        )

    def ensure_default_character_wearables(self) -> dict[str, Asset]:
        defaults = {
            "top": {
                "slug": "default-white-t-shirt",
                "display_name": "White T-Shirt / 白色 T恤",
                "description": "Simple clean white T-shirt for a neutral default character outfit.",
                "wearable_type": "top",
            },
            "bottom": {
                "slug": "default-blue-jeans",
                "display_name": "Blue Jeans / 蓝色牛仔裤",
                "description": "Classic blue denim jeans for a neutral default character outfit.",
                "wearable_type": "bottom",
            },
        }

        existing = {
            asset.slug: asset
            for asset in self.repository.list_assets(AssetType.WEARABLE)
        }
        result: dict[str, Asset] = {}

        for slot, spec in defaults.items():
            asset = existing.get(spec["slug"])
            if asset is None:
                asset = Asset.create(
                    AssetType.WEARABLE,
                    display_name=spec["display_name"],
                    slug=spec["slug"],
                    description=spec["description"],
                    status=ReviewStatus.APPROVED,
                    metadata={"wearable_type": spec["wearable_type"], "system_default": True},
                )
                self.repository.save_asset(asset)
            result[slot] = asset

        return result


    def archive_character(self, asset_id: str) -> Asset:
        """Soft-delete a Character so existing Story/World references do not break."""
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {asset_id}")
        asset.status = ReviewStatus.ARCHIVED
        self.repository.save_asset(asset)
        return asset
