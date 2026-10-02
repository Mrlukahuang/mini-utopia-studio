from dataclasses import dataclass
from studio.models.character import CharacterProfile
from studio.plugins.base import PluginRegistry
from studio.services.asset_service import AssetService


@dataclass
class CharacterFactoryRecipe:
    registry: PluginRegistry
    asset_service: AssetService

    def parse_description(self, description: str) -> CharacterProfile:
        return self.registry.get("character.parse").execute(description=description)

    def save_character(
        self,
        *,
        name: str,
        description: str,
        profile: CharacterProfile,
        asset_id: str | None = None,
    ):
        if asset_id:
            return self.asset_service.update_character(
                asset_id=asset_id,
                name=name,
                description=description,
                profile=profile,
            )
        return self.asset_service.create_character(
            name=name,
            description=description,
            profile=profile,
        )
