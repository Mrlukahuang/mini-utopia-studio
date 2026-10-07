from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.episode import DialogueLine, Episode
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.audio_timeline_service import AudioTimelineService
from studio.services.episode_service import EpisodeService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService


ROOT = Path(__file__).resolve().parents[1]


def _episode(repo: SQLiteStudioRepository):
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

    story = StoryService(repo).create_story(
        title="Audio Adventure",
        premise="Nancy speaks while exploring.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy enters the square.",
        discovery="Nancy finds a glowing clue.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    episode = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )
    return character, episode


def test_old_episode_payload_defaults_to_empty_audio_timeline():
    episode = Episode.model_validate(
        {
            "episode_id": "EP_OLD",
            "story_id": "STORY_OLD",
            "title": "Old Episode",
        }
    )
    assert episode.audio_timeline == []


def test_baseline_uses_existing_shot_dialogue_and_real_scene_narration(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, episode = _episode(repo)

    first_scene = episode.scenes[0]
    first_scene.dialogue_notes = "Nancy takes her first careful step."
    first_scene.shots[0].dialogue = [
        DialogueLine(
            character_asset_id=character.asset_id,
            text="Nova, did you see that light?",
            emotion="curious",
        )
    ]
    repo.save_episode(episode)

    built = AudioTimelineService(repo).ensure_baseline(
        episode.episode_id,
        replace=True,
    )

    assert len(built.audio_timeline) == 2
    dialogue = next(
        line
        for line in built.audio_timeline
        if line.speaker_kind == "character"
    )
    narration = next(
        line
        for line in built.audio_timeline
        if line.speaker_kind == "narrator"
    )

    assert dialogue.speaker_asset_id == character.asset_id
    assert dialogue.text == "Nova, did you see that light?"
    assert dialogue.emotion == "curious"
    assert narration.text == "Nancy takes her first careful step."
    assert narration.speaker_asset_id is None
    assert dialogue.start_seconds >= 0.0
    assert dialogue.duration_seconds > 0.0


def test_default_placeholder_note_never_becomes_narration(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _character, episode = _episode(repo)

    built = AudioTimelineService(repo).ensure_baseline(
        episode.episode_id,
        replace=True,
    )
    assert built.audio_timeline == []


def test_generation_is_idempotent_and_edits_approval_survive_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    character, episode = _episode(repo)
    episode.scenes[0].shots[0].dialogue = [
        DialogueLine(
            character_asset_id=character.asset_id,
            text="Let's go, Nova!",
            emotion="excited",
        )
    ]
    repo.save_episode(episode)

    service = AudioTimelineService(repo)
    first = service.ensure_baseline(
        episode.episode_id,
        replace=True,
    )
    line_id = first.audio_timeline[0].line_id
    second = service.ensure_baseline(episode.episode_id)
    assert [line.line_id for line in second.audio_timeline] == [line_id]

    service.update_line(
        episode_id=episode.episode_id,
        line_id=line_id,
        speaker_kind="character",
        speaker_asset_id=character.asset_id,
        text="Let's go, Nova!",
        start_seconds=0.4,
        duration_seconds=1.6,
        emotion="excited",
        delivery_note="Bright and warm",
        approved=True,
    )

    restarted = SQLiteStudioRepository(db_path)
    saved = restarted.get_episode(episode.episode_id)
    assert saved is not None
    assert len(saved.audio_timeline) == 1
    line = saved.audio_timeline[0]
    assert line.line_id == line_id
    assert line.approved is True
    assert line.start_seconds == 0.4
    assert line.duration_seconds == 1.6
    assert line.delivery_note == "Bright and warm"
    assert line.source == "creator"


def test_creator_narration_and_overlap_summary(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _character, episode = _episode(repo)
    service = AudioTimelineService(repo)

    scene = episode.scenes[0]
    shot = scene.shots[0]
    service.add_narration(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        text="First narration.",
    )
    current = repo.get_episode(episode.episode_id)
    assert current is not None
    first = current.audio_timeline[0]

    service.add_narration(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        text="Second narration overlaps.",
    )
    summary = service.summary(episode.episode_id)

    assert summary.line_count == 2
    assert len(summary.overlap_line_ids) == 2
    assert first.line_id in summary.overlap_line_ids
    assert summary.total_spoken_seconds > 0.0


def test_audio_timeline_is_visible_in_episode_creator():
    episodes_ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    audio_ui = (
        ROOT / "studio" / "ui" / "creator" / "audio_timeline.py"
    ).read_text(encoding="utf-8")

    assert "render_audio_timeline(" in episodes_ui
    assert "Dialogue & Narration / 对白与旁白" in audio_ui
    assert "Build Audio Timeline / 生成对白时间轨" in audio_ui
    assert "Add Narration / 添加旁白" in audio_ui
    assert "Approved / 已确认文字与时间" in audio_ui
    assert "Timeline overlap / 时间重叠" in audio_ui
