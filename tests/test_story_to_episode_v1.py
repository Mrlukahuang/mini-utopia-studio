from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.baby import BabyCompanion, BabyRoster
from studio.models.character import CharacterProfile
from studio.models.episode import Episode
from studio.models.story import Story
from studio.models.universe import Universe
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.episode_service import EpisodeService
from studio.services.story_service import StoryService


ROOT = Path(__file__).resolve().parents[1]


def _setup(repo: SQLiteStudioRepository):
    universe = Universe(
        universe_id="UNIV_EPISODE_TEST",
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


def test_legacy_episode_payload_remains_compatible():
    episode = Episode.model_validate(
        {
            "episode_id": "EP_OLD",
            "universe_id": "UNIV_OLD",
            "story_id": "STORY_OLD",
            "title": "Old Episode",
            "scenes": [],
        }
    )
    assert episode.mode == StoryMode.PLAYGROUND
    assert episode.asset_ids == []
    assert episode.world_asset_id is None
    assert episode.active_baby_id is None
    assert episode.continuity_memory_ids == []


def test_story_to_episode_is_idempotent_and_persists_references(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    universe, character, world = _setup(repo)

    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    active_baby = babies.active_baby()
    assert active_baby is not None

    story = StoryService(repo).create_story(
        title="The First Portal",
        premise="Nancy and Nova discover a Portal clue.",
        mode=StoryMode.CANON,
        universe_id=universe.universe_id,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives.",
        ending="The Portal wakes up.",
    )

    service = EpisodeService(repo)
    first = service.create_from_story(story.story_id)
    second = service.create_from_story(story.story_id)

    assert second.episode_id == first.episode_id
    assert first.story_id == story.story_id
    assert first.universe_id == universe.universe_id
    assert first.mode == StoryMode.CANON
    assert first.asset_ids == story.asset_ids
    assert first.world_asset_id == world.asset_id
    assert first.active_baby_id == active_baby.baby_id
    assert first.continuity_memory_ids

    restarted = EpisodeService(SQLiteStudioRepository(db_path))
    loaded = restarted.get_episode(first.episode_id)
    assert loaded == first
    assert len(restarted.list_episodes()) == 1


def test_playground_story_can_create_noncanon_episode_without_universe(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _universe, character, world = _setup(repo)
    story = StoryService(repo).create_story(
        title="Banana Moon",
        premise="A silly Playground experiment.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
    )

    episode = EpisodeService(repo).create_from_story(story.story_id)

    assert episode.mode == StoryMode.PLAYGROUND
    assert episode.universe_id is None
    assert episode.continuity_memory_ids == []
    assert episode.asset_ids == story.asset_ids


def test_episode_creator_flow_is_visible_and_both_backends_persist_episode():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    sqlite = (
        ROOT / "studio" / "repositories" / "sqlite.py"
    ).read_text(encoding="utf-8")
    supabase = (
        ROOT / "studio" / "repositories" / "supabase.py"
    ).read_text(encoding="utf-8")

    assert '"🎬 Episodes"' in app
    assert "Create Episode / 制作剧集" in app
    assert "render_episode_library(ctx)" in app
    assert "Episodes / 剧集" in ui
    assert "episodes" in sqlite
    assert "save_episode" in sqlite
    assert 'kind="episode"' in supabase
    assert "list_episodes" in supabase
