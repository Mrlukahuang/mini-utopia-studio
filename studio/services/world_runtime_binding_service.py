from __future__ import annotations

from collections import Counter

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset, now_utc
from studio.models.world import GridSpec, SpawnPoint, WorldBlueprint, WorldProfile
from studio.models.world_runtime import GodotWorldSceneBinding
from studio.repositories.base import StudioRepository


WORLD_RUNTIME_METADATA_KEY = "godot_scene_binding"

NEWBIE_WORLD_ASSET_ID = "LOC_SYSTEM_NEWBIE_VILLAGE_V03"
NEWBIE_WORLD_SCENE_PATH = "res://scenes/newbie_village_100x100_v0_3.tscn"


class WorldRuntimeBindingService:
    """Own the stable bridge between Creator World Assets and Godot scenes."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def binding_for(
        self,
        world_asset_id: str,
    ) -> GodotWorldSceneBinding | None:
        asset = self.repository.get_asset(world_asset_id)
        if asset is None or asset.asset_type != AssetType.LOCATION:
            return None
        raw = asset.metadata.get(WORLD_RUNTIME_METADATA_KEY)
        if not raw:
            return None
        return GodotWorldSceneBinding.model_validate(raw)

    def bind_scene(
        self,
        *,
        world_asset_id: str,
        scene_path: str,
        scene_label: str = "",
        source: str = "creator",
    ) -> GodotWorldSceneBinding:
        asset = self.repository.get_asset(world_asset_id)
        if asset is None or asset.asset_type != AssetType.LOCATION:
            raise ValueError(f"World not found: {world_asset_id}")

        binding = GodotWorldSceneBinding(
            world_asset_id=world_asset_id,
            scene_path=scene_path,
            scene_label=scene_label,
            source=source,
        )
        asset.metadata[WORLD_RUNTIME_METADATA_KEY] = binding.model_dump(mode="json")
        asset.updated_at = now_utc()
        self.repository.save_asset(asset)
        return binding

    def ensure_builtin_worlds(self) -> list[Asset]:
        """Register playable built-in Godot worlds without touching user Worlds."""

        worlds = self.repository.list_assets(AssetType.LOCATION)

        # If any existing Creator World is already bound to the scene, reuse it.
        for world in worlds:
            raw = world.metadata.get(WORLD_RUNTIME_METADATA_KEY)
            if not raw:
                continue
            binding = GodotWorldSceneBinding.model_validate(raw)
            if binding.scene_path == NEWBIE_WORLD_SCENE_PATH:
                return [world]

        existing = self.repository.get_asset(NEWBIE_WORLD_ASSET_ID)
        if existing is not None:
            if existing.asset_type != AssetType.LOCATION:
                raise ValueError(
                    f"Reserved Newbie World ID is not a World: {NEWBIE_WORLD_ASSET_ID}"
                )
            if not existing.metadata.get(WORLD_RUNTIME_METADATA_KEY):
                self.bind_scene(
                    world_asset_id=existing.asset_id,
                    scene_path=NEWBIE_WORLD_SCENE_PATH,
                    scene_label="Newbie Village 100×100 v0.3",
                    source="system_builtin",
                )
            return [self.repository.get_asset(existing.asset_id)]

        profile = WorldProfile(
            world_name="新手村 / Newbie Village",
            world_type="Toy Mountain Village",
            reality_mode="Mini Utopia",
            story_function="First Adventure Hub",
            terrain=["grass blocks", "terraced hills"],
            mood=["warm", "playful", "adventurous"],
            landmark_ideas=[
                "Village Main Road",
                "Training Skeleton",
                "Mountain Houses",
            ],
            portal_form="Village Portal",
            traversability_notes="Playable 100×100 Godot baseline world.",
            playable=True,
        )
        blueprint = WorldBlueprint(
            location_asset_id=NEWBIE_WORLD_ASSET_ID,
            grid=GridSpec(
                width=100,
                depth=100,
                cell_size=1.0,
                chunk_width=10,
                chunk_depth=10,
            ),
            # Match the actual Player start in the bound Godot scene so
            # Director blocking and gameplay share one physical frame.
            spawn=SpawnPoint(x=0.0, y=1.0, z=34.0, facing_degrees=0.0),
        )
        binding = GodotWorldSceneBinding(
            world_asset_id=NEWBIE_WORLD_ASSET_ID,
            scene_path=NEWBIE_WORLD_SCENE_PATH,
            scene_label="Newbie Village 100×100 v0.3",
            source="system_builtin",
        )
        asset = Asset(
            asset_id=NEWBIE_WORLD_ASSET_ID,
            asset_type=AssetType.LOCATION,
            display_name="新手村 / Newbie Village",
            slug="newbie-village-100x100-v0-3",
            description=(
                "Built-in playable Mini Utopia baseline bound to the existing "
                "Godot Newbie Village scene."
            ),
            status=ReviewStatus.APPROVED,
            metadata={
                "world_profile": profile.model_dump(mode="json"),
                "world_blueprint": blueprint.model_dump(mode="json"),
                "world_creation_complete": True,
                "world_pipeline": "godot_builtin_v1",
                "system_builtin": True,
                WORLD_RUNTIME_METADATA_KEY: binding.model_dump(mode="json"),
            },
        )
        self.repository.save_asset(asset)
        return [asset]

    def choice_labels(self, worlds: list[Asset]) -> dict[str, str]:
        """Disambiguate duplicate display names without merging/deleting data."""

        counts = Counter(world.display_name for world in worlds)
        labels: dict[str, str] = {}
        for world in worlds:
            label = world.display_name
            binding = self.binding_for(world.asset_id)
            if binding is not None:
                label += " · 🎮"
            if counts[world.display_name] > 1:
                label += f" · {world.asset_id[-6:]}"
            labels[world.asset_id] = label
        return labels
