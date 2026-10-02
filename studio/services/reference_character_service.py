from __future__ import annotations

import json

from studio.core.enums import AssetType
from studio.models.reference import ReferenceCharacterConfig
from studio.repositories.base import StudioRepository
from studio.storage.base import ObjectStorage


REFERENCE_CONFIG_PATH = "settings/reference_characters.json"


class ReferenceCharacterService:
    """Persist and resolve Studio-level reference Character anchors.

    The config stores only CHAR_IDs. Character names and measurements continue
    to live on the normal Character Assets themselves.
    """

    def __init__(self, repository: StudioRepository, storage: ObjectStorage):
        self.repository = repository
        self.storage = storage

    def load(self) -> ReferenceCharacterConfig | None:
        if not self.storage.exists(REFERENCE_CONFIG_PATH):
            return None
        payload = json.loads(
            self.storage.get_bytes(REFERENCE_CONFIG_PATH).decode("utf-8")
        )
        return ReferenceCharacterConfig.model_validate(payload)

    def save(self, config: ReferenceCharacterConfig) -> ReferenceCharacterConfig:
        for asset_id in config.character_asset_ids:
            asset = self.repository.get_asset(asset_id)
            if asset is None or asset.asset_type != AssetType.CHARACTER:
                raise ValueError(f"Reference asset is not a Character: {asset_id}")
        self.storage.put_bytes(
            REFERENCE_CONFIG_PATH,
            config.model_dump_json(indent=2).encode("utf-8"),
        )
        return config

    def clear(self) -> None:
        path = self.storage.resolve(REFERENCE_CONFIG_PATH)
        if path.exists():
            path.unlink()

    def eligible_characters(self):
        eligible = []
        for asset in self.repository.list_assets(AssetType.CHARACTER):
            profile = asset.metadata.get("character_profile", {})
            height_cm = profile.get("height_cm")
            if isinstance(height_cm, (int, float)) and height_cm > 0:
                eligible.append(asset)
        return eligible

    def resolved_anchors(self):
        config = self.load()
        if config is None:
            return None

        assets = [
            self.repository.get_asset(asset_id)
            for asset_id in config.character_asset_ids
        ]
        if any(asset is None for asset in assets):
            return None

        heights = [
            float(asset.metadata["character_profile"]["height_cm"])
            for asset in assets
        ]
        return config, assets, heights
