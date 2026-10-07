from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.story import Story
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.episode_service import EpisodeService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.story_service import StoryService


ROOT = Path(__file__).resolve().parents[1]


def _assets(repo: SQLiteStudioRepository):
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
    return character, world


def test_story_six_beats_builds_six_ordered_scenes_with_same_assets(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, world = _assets(repo)
    story = StoryService(repo).create_story(
        title="Portal Adventure",
        premise="Nancy follows a Portal mystery.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives at the village.",
        discovery="She finds a glowing clue.",
        conflict="A closed gate blocks the path.",
        adventure="Nancy explores and solves the gate puzzle.",
        twist="The clue belongs to a friendly guardian.",
        ending="A Portal opens to the next World.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)

    built = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )

    assert [scene.story_beat for scene in built.scenes] == [
        "ARRIVE",
        "DISCOVER",
        "PROBLEM",
        "ADVENTURE",
        "SURPRISE",
        "PORTAL",
    ]
    assert [scene.scene_id for scene in built.scenes] == [
        "SCENE_01",
        "SCENE_02",
        "SCENE_03",
        "SCENE_04",
        "SCENE_05",
        "SCENE_06",
    ]
    for scene in built.scenes:
        assert scene.location_asset_id == world.asset_id
        assert scene.asset_ids == story.asset_ids
        assert scene.description
        assert scene.action_summary
        assert f"Source Story: {story.story_id}" in scene.continuity_notes


def test_blank_beats_are_skipped_and_existing_edit_is_not_replaced_without_confirmation(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, world = _assets(repo)
    story = StoryService(repo).create_story(
        title="Small Story",
        premise="A short adventure.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Arrive.",
        adventure="Explore.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    service = SceneBreakdownService(repo)

    built = service.build_from_story(episode.episode_id)
    assert [scene.story_beat for scene in built.scenes] == [
        "ARRIVE",
        "ADVENTURE",
    ]

    edited = service.update_scene(
        episode_id=episode.episode_id,
        scene_id="SCENE_01",
        title="My Edited Arrival",
        description="A creator-edited scene.",
        action_summary="Nancy waves.",
        dialogue_notes="Nancy: Hello!",
        continuity_notes=["Keep Nova beside Nancy."],
    )
    assert edited.scenes[0].title == "My Edited Arrival"

    unchanged = service.build_from_story(episode.episode_id)
    assert unchanged.scenes[0].title == "My Edited Arrival"

    rebuilt = service.build_from_story(
        episode.episode_id,
        replace=True,
    )
    assert rebuilt.scenes[0].title.startswith("Arrive")
    assert rebuilt.scenes[0].description == "Arrive."


def test_scene_edits_survive_full_sqlite_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    character, world = _assets(repo)
    story = StoryService(repo).create_story(
        title="Persisted Production",
        premise="A Story becomes a production plan.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy enters.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    service = SceneBreakdownService(repo)
    service.build_from_story(episode.episode_id)
    service.update_scene(
        episode_id=episode.episode_id,
        scene_id="SCENE_01",
        title="Opening Wide",
        description="Nancy enters beneath the village arch.",
        action_summary="Walk into frame and pause.",
        dialogue_notes="Narrator welcomes the audience.",
        continuity_notes=["Crown stays equipped.", "Nova follows."],
    )

    restarted = SQLiteStudioRepository(db_path)
    loaded = EpisodeService(restarted).get_episode(episode.episode_id)
    assert loaded is not None
    assert len(loaded.scenes) == 1
    scene = loaded.scenes[0]
    assert scene.title == "Opening Wide"
    assert scene.action_summary == "Walk into frame and pause."
    assert scene.dialogue_notes == "Narrator welcomes the audience."
    assert scene.continuity_notes == [
        "Crown stays equipped.",
        "Nova follows.",
    ]


def test_episode_page_exposes_scene_build_edit_and_explicit_rebuild():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "Build Script & Scenes / 拆成场景" in ui
    assert "Script & Scene Breakdown / 剧本场景" in ui
    assert "Save Scene / 保存场景" in ui
    assert "Rebuild from Story / 按故事重建" in ui
    assert "重建会覆盖 Scene 文本编辑" in ui
    assert "scene_service.update_scene(" in ui
