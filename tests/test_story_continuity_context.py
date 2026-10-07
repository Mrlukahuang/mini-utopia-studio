from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.story import Story
from studio.models.world import WorldProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.story_continuity_service import StoryContinuityService
from studio.services.world_creative_layout_service import WorldCreativeLayoutService
from studio.models.world_creative import CreativePropType


ROOT = Path(__file__).resolve().parents[1]


def _character(repo: SQLiteStudioRepository, name: str = "Nancy") -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name=name,
        slug=name.lower(),
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def _world(repo: SQLiteStudioRepository, name: str = "Newbie Village") -> Asset:
    asset = Asset.create(
        AssetType.LOCATION,
        display_name=name,
        slug=name.lower().replace(" ", "-"),
        metadata={
            "world_profile": WorldProfile(
                world_name=name,
                world_type="Toy Village",
                mood=["warm", "curious"],
                landmark_ideas=["Village Square", "Star Portal"],
                portal_form="Star Arch",
            ).model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def test_continuity_snapshot_is_strictly_read_only_on_empty_state(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    world = _world(repo)

    before_assets = repo.list_assets()
    assert repo.get_collection("COLL_DEFAULT") is None
    assert repo.get_baby_roster("BABIES_DEFAULT") is None

    context = StoryContinuityService(repo).build(
        character_asset_ids=[character.asset_id],
        world_asset_id=world.asset_id,
        universe_id="UNIV_MINI_UTOPIA",
    )

    assert context.has_context is True
    assert len(context.character_states) == 1
    assert context.character_states[0].final_hp == 100
    assert context.active_baby is None
    assert context.important_owned_items == []
    assert repo.get_collection("COLL_DEFAULT") is None
    assert repo.get_baby_roster("BABIES_DEFAULT") is None
    assert [asset.asset_id for asset in repo.list_assets()] == [
        asset.asset_id for asset in before_assets
    ]


def test_canon_continuity_survives_restart_and_scopes_prior_stories(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    nancy = _character(repo, "Nancy")
    chelsea = _character(repo, "Chelsea")
    world = _world(repo)
    other_world = _world(repo, "Cloud Garden")

    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Nova star",
        species_id="star_baby",
    )
    baby = babies.active_baby()
    assert baby is not None
    babies.add_xp(baby_id=baby.baby_id, amount=75)
    babies.add_bond(baby_id=baby.baby_id, amount=12)

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    sword = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot.value == "weapon_main"
    )
    equipment.equip(
        character_asset_id=nancy.asset_id,
        item_instance_id=sword.item_instance_id,
    )
    equipment.set_favorite(
        item_instance_id=sword.item_instance_id,
        favorite=True,
    )

    WorldCreativeLayoutService(repo).place(
        world_asset_id=world.asset_id,
        prop_type=CreativePropType.STAR_LAMP,
        position=(25.0, 0.0, 27.0),
    )

    matching = Story(
        story_id="STORY_MATCH",
        title="The First Portal Clue",
        premise="Nancy and Nova find a clue in Newbie Village.",
        mode=StoryMode.CANON,
        universe_id="UNIV_MINI_UTOPIA",
        asset_ids=[nancy.asset_id, world.asset_id],
        hook="Nancy arrives at the square.",
        discovery="Nova spots a glowing mark.",
    )
    unrelated_character = Story(
        story_id="STORY_OTHER_CHARACTER",
        title="Chelsea Elsewhere",
        premise="Chelsea explores without Nancy.",
        mode=StoryMode.CANON,
        universe_id="UNIV_MINI_UTOPIA",
        asset_ids=[chelsea.asset_id, world.asset_id],
    )
    unrelated_world = Story(
        story_id="STORY_OTHER_WORLD",
        title="Nancy in Cloud Garden",
        premise="Nancy visits a different World.",
        mode=StoryMode.CANON,
        universe_id="UNIV_MINI_UTOPIA",
        asset_ids=[nancy.asset_id, other_world.asset_id],
    )
    playground = Story(
        story_id="STORY_PLAYGROUND",
        title="Silly Playground",
        premise="Not Canon.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[nancy.asset_id, world.asset_id],
    )
    for story in (
        matching,
        unrelated_character,
        unrelated_world,
        playground,
    ):
        repo.save_story(story)

    restarted = SQLiteStudioRepository(db_path)
    context = StoryContinuityService(restarted).build(
        character_asset_ids=[nancy.asset_id],
        world_asset_id=world.asset_id,
        universe_id="UNIV_MINI_UTOPIA",
    )

    assert len(context.character_states) == 1
    hero = context.character_states[0]
    assert hero.display_name == "Nancy"
    assert hero.final_atk > 10
    assert [item.display_name for item in hero.equipped] == [
        "Starwood Sword / 星木剑"
    ]

    assert context.active_baby is not None
    assert context.active_baby.display_name == "Nova star"
    assert context.active_baby.xp == 75
    assert context.active_baby.bond == 12

    assert context.important_owned_items
    favorite = next(
        item
        for item in context.important_owned_items
        if item.item_instance_id == sword.item_instance_id
    )
    assert favorite.favorite is True

    assert context.world is not None
    assert context.world.display_name == "Newbie Village"
    assert context.world.creative_decoration_count == 1

    assert [story.story_id for story in context.prior_canon_stories] == [
        "STORY_MATCH"
    ]


def test_story_builder_visibly_uses_canon_continuity_only_for_canon_suggestions():
    builder = (
        ROOT / "studio" / "ui" / "creator" / "story_builder.py"
    ).read_text(encoding="utf-8")
    suggestions = (
        ROOT / "studio" / "services" / "story_suggestion_service.py"
    ).read_text(encoding="utf-8")

    assert "StoryContinuityService(ctx.repository).build(" in builder
    assert "Canon Continuity / 连续性已连接" in builder
    assert "story_mode == StoryMode.CANON" in builder
    assert "continuity_context=(" in builder
    assert "continuity_context: dict | None = None" in suggestions
    assert '"continuity": continuity_context or {}' in suggestions
    assert "Never rewrite or contradict prior Canon events" in suggestions
