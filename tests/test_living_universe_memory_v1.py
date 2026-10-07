from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.baby import create_baby_companion
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentRarity, create_equipment_instance
from studio.models.story import Story
from studio.models.universe import Universe
from studio.models.universe_memory import (
    UniverseMemoryKind,
    memory_id_for_source,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.living_universe_memory_service import (
    LivingUniverseMemoryService,
)
from studio.services.story_continuity_service import StoryContinuityService
from studio.services.story_service import StoryService


ROOT = Path(__file__).resolve().parents[1]


def _setup(repo: SQLiteStudioRepository):
    universe = Universe(
        universe_id="UNIV_MEMORY_TEST",
        name="Mini Utopia",
    )
    repo.save_universe(universe)
    character = Asset.create(
        AssetType.CHARACTER,
        display_name="Nancy",
        slug="nancy",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Newbie Village",
        slug="newbie-village",
    )
    repo.save_asset(character)
    repo.save_asset(world)
    return universe, character, world


def test_saved_canon_story_writes_one_idempotent_memory_but_playground_does_not(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    universe, character, world = _setup(repo)
    stories = StoryService(repo)

    canon = stories.create_story(
        title="The Portal Clue",
        premise="Nancy finds a glowing clue.",
        mode=StoryMode.CANON,
        universe_id=universe.universe_id,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives.",
        discovery="A clue glows beside the Portal.",
    )
    playground = stories.create_story(
        title="Banana Moon",
        premise="A silly experiment.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
    )

    service = LivingUniverseMemoryService(repo)
    memories = service.list(universe_id=universe.universe_id)
    assert len(memories) == 1
    assert memories[0].story_id == canon.story_id
    assert memories[0].kind == UniverseMemoryKind.CANON_STORY
    assert playground.story_id not in {
        memory.story_id for memory in memories
    }

    memory_id = memories[0].memory_id
    service.ingest_story(canon)
    service.ingest_story(canon)
    memories_again = service.list(universe_id=universe.universe_id)
    assert len(memories_again) == 1
    assert memories_again[0].memory_id == memory_id
    assert memory_id == memory_id_for_source(
        universe.universe_id,
        f"story:{canon.story_id}",
    )


def test_living_memory_syncs_world_baby_reward_and_survives_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    universe, character, world = _setup(repo)

    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Nova star",
        species_id="star_baby",
    )
    baby = babies.active_baby()
    assert baby is not None
    babies.add_xp(baby_id=baby.baby_id, amount=125)
    babies.add_bond(baby_id=baby.baby_id, amount=18)

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    reward_asset = next(
        asset
        for asset in repo.list_assets(AssetType.EQUIPMENT)
        if asset.slug == "reward_bone_buckler"
    )
    reward_definition = definitions[reward_asset.asset_id]
    reward = create_equipment_instance(
        definition=reward_definition,
        rarity=EquipmentRarity.BLUE,
        generation_seed="MEMORY_BONE_BUCKLER",
    )
    collection.items.append(reward)
    repo.save_collection(collection)

    stories = StoryService(repo)
    canon = stories.create_story(
        title="Skeleton Surprise",
        premise="Nancy wins a reward and the Portal wakes up.",
        mode=StoryMode.CANON,
        universe_id=universe.universe_id,
        asset_ids=[character.asset_id, world.asset_id],
        adventure="Nancy defeats the Training Skeleton.",
        ending="The Portal lights up.",
    )

    service = LivingUniverseMemoryService(repo)
    first = service.sync_known_state(universe_id=universe.universe_id)
    second = service.sync_known_state(universe_id=universe.universe_id)

    assert len(second) == len(first)
    kinds = {memory.kind for memory in second}
    assert UniverseMemoryKind.CANON_STORY in kinds
    assert UniverseMemoryKind.WORLD_DISCOVERY in kinds
    assert UniverseMemoryKind.BABY_MILESTONE in kinds
    assert UniverseMemoryKind.ITEM_ACQUIRED in kinds

    baby_memory = next(
        memory
        for memory in second
        if memory.kind == UniverseMemoryKind.BABY_MILESTONE
    )
    assert "Lv.2" in baby_memory.summary
    assert "Bond 18" in baby_memory.summary

    reward_memory = next(
        memory
        for memory in second
        if memory.kind == UniverseMemoryKind.ITEM_ACQUIRED
    )
    assert "Bone Buckler" in reward_memory.summary
    assert reward_memory.item_instance_id == reward.item_instance_id

    restarted = SQLiteStudioRepository(db_path)
    persisted = LivingUniverseMemoryService(restarted).list(
        universe_id=universe.universe_id
    )
    assert {memory.memory_id for memory in persisted} == {
        memory.memory_id for memory in second
    }

    continuity = StoryContinuityService(restarted).build(
        character_asset_ids=[character.asset_id],
        world_asset_id=world.asset_id,
        universe_id=universe.universe_id,
    )
    assert continuity.living_memory
    assert any(
        memory.kind == "canon_story"
        and canon.title in memory.summary
        for memory in continuity.living_memory
    )
    assert any(
        memory.kind == "world_discovery"
        for memory in continuity.living_memory
    )


def test_living_memory_is_visible_on_universe_page_and_repository_backends_support_it():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ui = (
        ROOT / "studio" / "ui" / "creator" / "universe_memory.py"
    ).read_text(encoding="utf-8")
    sqlite = (
        ROOT / "studio" / "repositories" / "sqlite.py"
    ).read_text(encoding="utf-8")
    supabase = (
        ROOT / "studio" / "repositories" / "supabase.py"
    ).read_text(encoding="utf-8")

    assert "render_universe_memory(" in app
    assert "Living Universe Memory / 宇宙记忆" in ui
    assert "sync_known_state(" in ui
    assert "universe_memories" in sqlite
    assert "save_universe_memory" in sqlite
    assert 'kind="universe_memory"' in supabase
    assert "list_universe_memories" in supabase
