from __future__ import annotations

from studio.core.enums import AssetType, ReviewStatus, StoryMode
from studio.models.character import CharacterProfile
from studio.models.equipment import PLAYABLE_EQUIPMENT_SLOTS
from studio.models.story_continuity import (
    ContinuityBabyState,
    ContinuityCharacterState,
    ContinuityEquipmentItem,
    ContinuityOwnedItem,
    ContinuityStoryState,
    ContinuityWorldState,
    StoryContinuityContext,
)
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.world_creative_layout_service import WorldCreativeLayoutService
from studio.services.world_gameplay_layer_service import WorldGameplayLayerService


class StoryContinuityService:
    """Build a read-only Canon continuity snapshot from durable Creator state."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository
        self.equipment = EquipmentService(repository)
        self.babies = BabyService(repository)

    def build(
        self,
        *,
        character_asset_ids: list[str],
        world_asset_id: str | None,
        universe_id: str | None = None,
    ) -> StoryContinuityContext:
        selected_ids = list(dict.fromkeys(character_asset_ids))
        definitions = self.equipment.list_definitions()
        collection = self.equipment.ensure_starter_collection()

        character_states: list[ContinuityCharacterState] = []
        equipped_item_ids: set[str] = set()
        for character_id in selected_ids:
            asset = self.repository.get_asset(character_id)
            if asset is None or asset.asset_type != AssetType.CHARACTER:
                continue
            if asset.status == ReviewStatus.ARCHIVED:
                continue

            profile = CharacterProfile.model_validate(
                asset.metadata.get("character_profile", {})
            )
            final_stats = self.equipment.final_stats(character_id)
            loadout = collection.loadout_for(character_id)
            equipped: list[ContinuityEquipmentItem] = []
            for slot in PLAYABLE_EQUIPMENT_SLOTS:
                item_id = loadout.item_id_for_slot(slot)
                if not item_id:
                    continue
                item = collection.item_by_id(item_id)
                definition = (
                    definitions.get(item.definition_id)
                    if item is not None
                    else None
                )
                if item is None or definition is None:
                    continue
                equipped_item_ids.add(item.item_instance_id)
                equipped.append(
                    ContinuityEquipmentItem(
                        item_instance_id=item.item_instance_id,
                        display_name=definition.display_name,
                        slot=definition.slot.value,
                        rarity=item.rarity.value,
                        hp=item.rolled_stats.hp,
                        atk=item.rolled_stats.atk,
                        defense=item.rolled_stats.defense,
                    )
                )

            character_states.append(
                ContinuityCharacterState(
                    asset_id=asset.asset_id,
                    display_name=asset.display_name,
                    body_type=profile.avatar.body_type.value,
                    species_head_id=profile.avatar.species_head_id,
                    final_hp=final_stats.hp,
                    final_atk=final_stats.atk,
                    final_defense=final_stats.defense,
                    equipped=equipped,
                )
            )

        baby = self.babies.active_baby()
        active_baby = (
            ContinuityBabyState(
                baby_id=baby.baby_id,
                display_name=baby.display_name,
                species_id=baby.species_id,
                level=baby.level,
                xp=baby.xp,
                bond=baby.bond,
            )
            if baby is not None
            else None
        )

        # Favorites are always important; then include currently equipped and
        # newest items, bounded so Story prompts remain concise.
        favorite_ids = set(collection.favorite_item_ids)
        ordered_items = sorted(
            collection.items,
            key=lambda item: item.created_at,
            reverse=True,
        )
        important_ids: list[str] = []
        for item in ordered_items:
            if item.item_instance_id in favorite_ids:
                important_ids.append(item.item_instance_id)
        for item_id in equipped_item_ids:
            if item_id not in important_ids:
                important_ids.append(item_id)
        for item in ordered_items:
            if item.item_instance_id not in important_ids:
                important_ids.append(item.item_instance_id)
            if len(important_ids) >= 8:
                break

        important_owned_items: list[ContinuityOwnedItem] = []
        for item_id in important_ids[:8]:
            item = collection.item_by_id(item_id)
            definition = (
                definitions.get(item.definition_id)
                if item is not None
                else None
            )
            if item is None or definition is None:
                continue
            important_owned_items.append(
                ContinuityOwnedItem(
                    item_instance_id=item.item_instance_id,
                    display_name=definition.display_name,
                    slot=definition.slot.value,
                    rarity=item.rarity.value,
                    favorite=item.item_instance_id in favorite_ids,
                )
            )

        world_state = None
        if world_asset_id:
            world_asset = self.repository.get_asset(world_asset_id)
            if (
                world_asset is not None
                and world_asset.asset_type == AssetType.LOCATION
                and world_asset.status != ReviewStatus.ARCHIVED
            ):
                profile = world_asset.metadata.get("world_profile", {}) or {}
                gameplay = WorldGameplayLayerService(
                    self.repository
                ).get_layer(world_asset_id)
                creative = WorldCreativeLayoutService(
                    self.repository
                ).get_layout(world_asset_id)
                world_state = ContinuityWorldState(
                    asset_id=world_asset.asset_id,
                    display_name=world_asset.display_name,
                    world_type=str(profile.get("world_type", "")),
                    mood=list(profile.get("mood", []) or []),
                    landmarks=list(profile.get("landmark_ideas", []) or []),
                    portal_form=str(profile.get("portal_form", "")),
                    gameplay_modes=(
                        [mode.value for mode in gameplay.modes]
                        if gameplay is not None
                        else ["explore"]
                    ),
                    creative_decoration_count=len(creative.decorations),
                )

        prior: list[ContinuityStoryState] = []
        if world_asset_id and selected_ids:
            selected_set = set(selected_ids)
            candidates = [
                story
                for story in self.repository.list_stories()
                if story.mode == StoryMode.CANON
                and story.status != ReviewStatus.ARCHIVED
                and world_asset_id in story.asset_ids
                and bool(selected_set.intersection(story.asset_ids))
                and (
                    universe_id is None
                    or story.universe_id in (None, universe_id)
                )
            ]
            candidates.sort(key=lambda story: story.updated_at, reverse=True)
            for story in candidates[:5]:
                prior.append(
                    ContinuityStoryState(
                        story_id=story.story_id,
                        title=story.title,
                        premise=story.premise,
                        hook=story.hook,
                        discovery=story.discovery,
                        conflict=story.conflict,
                        adventure=story.adventure,
                        twist=story.twist,
                        ending=story.ending,
                    )
                )

        return StoryContinuityContext(
            character_states=character_states,
            active_baby=active_baby,
            important_owned_items=important_owned_items,
            world=world_state,
            prior_canon_stories=prior,
        )
