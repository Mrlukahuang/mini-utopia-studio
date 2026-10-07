from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.story import Story
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.play_session_service import CreatorPlaySessionService
from studio.services.story_playable_quest_service import (
    StoryPlayableQuestService,
)
from studio.storage.local import LocalObjectStorage


def _story_world(repo: SQLiteStudioRepository):
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
        story_id="STORY_PLAYABLE",
        title="The Glowing Portal",
        premise="Nancy discovers a clue guarded by a Skeleton.",
        mode=StoryMode.CANON,
        universe_id="UNIV_MINI_UTOPIA",
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives in Newbie Village.",
        discovery="Find the glowing clue.",
        conflict="A Skeleton blocks the road.",
        adventure="Win the Skeleton reward.",
        twist="The reward reacts to the Portal.",
        ending="Open the Portal to the next world.",
    )
    repo.save_story(story)
    return character, world, story


def test_structured_story_becomes_one_persisted_playable_quest(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _character, world, story = _story_world(repo)
    service = StoryPlayableQuestService(repo)

    quest = service.make_playable(story.story_id)
    assert quest.story_id == story.story_id
    assert quest.world_asset_id == world.asset_id
    assert quest.universe_id == story.universe_id
    assert [item.objective_type.value for item in quest.objectives] == [
        "go_to_location",
        "interact",
        "defeat_enemy",
        "collect_item",
        "open_portal",
    ]
    assert quest.objectives[1].label == story.discovery
    assert quest.objectives[2].label == story.conflict
    assert quest.objectives[-1].label == story.ending
    assert quest.objectives[1].metadata["position"] == [0.0, 0.45, 22.0]
    assert quest.objectives[-1].metadata["position"] == [0.0, 0.45, -30.0]

    # Conversion is idempotent: repeated clicks reuse the Story's Quest.
    assert service.make_playable(story.story_id).quest_id == quest.quest_id

    restarted = SQLiteStudioRepository(tmp_path / "studio.db")
    assert restarted.get_quest(quest.quest_id) == quest


def test_play_session_carries_same_story_quest_and_selects_its_world(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, world, story = _story_world(repo)
    quest = StoryPlayableQuestService(repo).make_playable(story.story_id)

    export_path = tmp_path / "creator_play_session.json"
    session = CreatorPlaySessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        export_path=export_path,
    ).export(
        character_asset_id=character.asset_id,
        quest_id=quest.quest_id,
    )

    assert session.quest == quest
    assert session.world_asset_id == world.asset_id
    assert session.world_name == "Newbie Village"
    assert session.quest.story_id == story.story_id

    payload = export_path.read_text(encoding="utf-8")
    assert '"quest"' in payload
    assert "training_skeleton_01" in payload
    assert "newbie_village_portal" in payload


def test_story_ui_and_godot_use_generic_quest_layer():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "app.py").read_text(encoding="utf-8")
    room = (
        root / "studio" / "ui" / "creator" / "dressing_room.py"
    ).read_text(encoding="utf-8")
    creator_runtime = (
        root / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")
    quest_runtime = (
        root / "godot" / "scripts" / "quest_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "Make Playable Quest / 变成可玩任务" in app
    assert "active_quest_id" in app
    assert "Active Quest" in room
    assert "quest_id=" in room
    assert "MiniUtopiaQuestRuntime" in creator_runtime
    assert "record_quest_event" in creator_runtime
    assert "func record_event(" in quest_runtime
    assert "func try_interact()" in quest_runtime
    assert "QuestHUD" in quest_runtime
