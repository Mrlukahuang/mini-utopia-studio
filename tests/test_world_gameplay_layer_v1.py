from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.story import Story
from studio.models.world_gameplay import WorldExperienceMode
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.play_session_service import CreatorPlaySessionService
from studio.services.story_playable_quest_service import (
    StoryPlayableQuestService,
)
from studio.services.world_gameplay_layer_service import (
    WorldGameplayLayerService,
)
from studio.storage.local import LocalObjectStorage


def _setup(repo: SQLiteStudioRepository):
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Newbie Village",
        slug="newbie-village",
    )
    character = Asset.create(
        AssetType.CHARACTER,
        display_name="Nancy",
        slug="nancy",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(world)
    repo.save_asset(character)
    story = Story(
        story_id="STORY_WORLD_LAYER",
        title="One World Adventure",
        premise="Use the same village as Explore, Quest and Story Play.",
        mode=StoryMode.CANON,
        universe_id="UNIV_MINI_UTOPIA",
        asset_ids=[character.asset_id, world.asset_id],
        hook="Arrive.",
        discovery="Discover the clue.",
        conflict="Defeat the Skeleton.",
        adventure="Claim the reward.",
        twist="The Portal wakes up.",
        ending="Open the Portal.",
    )
    repo.save_story(story)
    return character, world, story


def test_one_world_asset_supports_explore_quest_and_story_play(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    _character, world, story = _setup(repo)

    quest = StoryPlayableQuestService(repo).make_playable(story.story_id)
    layer = WorldGameplayLayerService(repo).get_layer(world.asset_id)

    assert layer is not None
    assert layer.world_asset_id == world.asset_id
    assert set(layer.modes) == {
        WorldExperienceMode.EXPLORE,
        WorldExperienceMode.QUEST,
        WorldExperienceMode.STORY_PLAY,
    }
    assert layer.quest_ids == [quest.quest_id]
    assert layer.story_ids == [story.story_id]

    target_ids = {target.target_id for target in layer.targets}
    assert "newbie_village_story_clue" in target_ids
    assert "training_skeleton_01" in target_ids
    assert "reward_bone_buckler" in target_ids
    assert "newbie_village_portal" in target_ids

    # Gameplay registration augments metadata; it never copies the Location.
    locations = repo.list_assets(AssetType.LOCATION)
    assert [asset.asset_id for asset in locations] == [world.asset_id]

    # Re-registering the same Story/Quest is idempotent.
    assert (
        StoryPlayableQuestService(repo).make_playable(story.story_id).quest_id
        == quest.quest_id
    )
    layer_again = WorldGameplayLayerService(repo).get_layer(world.asset_id)
    assert layer_again.quest_ids == [quest.quest_id]
    assert layer_again.story_ids == [story.story_id]

    restarted_repo = SQLiteStudioRepository(db_path)
    restarted = WorldGameplayLayerService(restarted_repo).get_layer(
        world.asset_id
    )
    assert restarted is not None
    assert restarted.world_asset_id == world.asset_id
    assert set(restarted.modes) == set(layer.modes)


def test_play_session_uses_same_world_for_quest_and_gameplay_layer(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, world, story = _setup(repo)
    quest = StoryPlayableQuestService(repo).make_playable(story.story_id)

    session = CreatorPlaySessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        export_path=tmp_path / "play_session.json",
    ).export(
        character_asset_id=character.asset_id,
        quest_id=quest.quest_id,
    )

    assert session.world_asset_id == world.asset_id
    assert session.quest is not None
    assert session.quest.world_asset_id == world.asset_id
    assert session.world_gameplay is not None
    assert session.world_gameplay.world_asset_id == world.asset_id
    assert quest.quest_id in session.world_gameplay.quest_ids
    assert story.story_id in session.world_gameplay.story_ids


def test_world_gameplay_layer_is_visible_and_consumed_by_godot():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "app.py").read_text(encoding="utf-8")
    creator = (
        root / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")
    runtime = (
        root / "godot" / "scripts" / "world_gameplay_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "One World · Multiple Ways to Play" in app
    assert "godot_play_session.world_gameplay" in app
    assert 'payload.get("world_gameplay", {})' in creator
    assert "MiniUtopiaWorldGameplayRuntime" in creator
    assert "func supports_mode(" in runtime
    assert "func target_by_id(" in runtime
