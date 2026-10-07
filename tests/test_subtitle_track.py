from pathlib import Path

from studio.core.enums import StoryMode
from studio.models.audio_timeline import EpisodeAudioLine
from studio.models.episode import Episode
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.subtitle_track_service import SubtitleTrackService


ROOT = Path(__file__).resolve().parents[1]


def _episode(repo: SQLiteStudioRepository) -> Episode:
    episode = Episode(
        episode_id="EP_SUB",
        story_id="STORY_SUB",
        title="Subtitle Adventure",
        mode=StoryMode.PLAYGROUND,
        audio_timeline=[
            EpisodeAudioLine(
                line_id="AUDIO_001",
                scene_id="SCENE_01",
                shot_id="SHOT_01_01",
                speaker_kind="narrator",
                text="Nancy enters the village.",
                start_seconds=0.5,
                duration_seconds=2.0,
                approved=True,
            ),
            EpisodeAudioLine(
                line_id="AUDIO_002",
                scene_id="SCENE_01",
                shot_id="SHOT_01_02",
                speaker_kind="narrator",
                text="Nova notices a light.",
                start_seconds=3.0,
                duration_seconds=1.5,
                approved=True,
            ),
        ],
    )
    repo.save_episode(episode)
    return episode


def test_old_episode_payload_defaults_to_empty_subtitle_track():
    episode = Episode.model_validate(
        {
            "episode_id": "EP_OLD",
            "story_id": "STORY_OLD",
            "title": "Old Episode",
        }
    )
    assert episode.subtitle_track == []


def test_subtitles_generate_deterministically_without_duplicates(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)
    service = SubtitleTrackService(
        repo,
        project_root=tmp_path / "project",
    )

    first = service.ensure_track(episode.episode_id)
    assert len(first.subtitle_track) == 2
    first_ids = [cue.cue_id for cue in first.subtitle_track]
    assert first.subtitle_track[0].text == "Nancy enters the village."
    assert first.subtitle_track[0].start_seconds == 0.5
    assert first.subtitle_track[0].end_seconds == 2.5
    assert first.subtitle_track[0].speaker_label == "Narrator"

    second = service.ensure_track(episode.episode_id)
    assert [cue.cue_id for cue in second.subtitle_track] == first_ids
    assert len(second.subtitle_track) == 2

    restarted = SQLiteStudioRepository(tmp_path / "studio.db")
    saved = restarted.get_episode(episode.episode_id)
    assert saved is not None
    assert [cue.cue_id for cue in saved.subtitle_track] == first_ids


def test_audio_change_marks_subtitle_stale_and_refreshes_only_subtitle(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)
    service = SubtitleTrackService(repo)
    built = service.ensure_track(episode.episode_id)
    cue = built.subtitle_track[0]

    current = repo.get_episode(episode.episode_id)
    current.audio_timeline[0] = current.audio_timeline[0].model_copy(
        update={
            "text": "Nancy quietly enters the village.",
            "duration_seconds": 2.4,
        }
    )
    repo.save_episode(current)

    assert service.status_for(
        episode_id=episode.episode_id,
        cue=cue,
    ) == "stale"

    refreshed = service.refresh_cue(
        episode_id=episode.episode_id,
        cue_id=cue.cue_id,
    )
    assert refreshed.text == "Nancy quietly enters the village."
    assert refreshed.end_seconds == 2.9
    assert refreshed.approved is False
    assert service.status_for(
        episode_id=episode.episode_id,
        cue=refreshed,
    ) == "ready"

    source = repo.get_episode(episode.episode_id).audio_timeline[0]
    assert source.text == "Nancy quietly enters the village."
    assert source.duration_seconds == 2.4


def test_creator_subtitle_edit_does_not_rewrite_audio_source(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)
    service = SubtitleTrackService(repo)
    cue = service.ensure_track(episode.episode_id).subtitle_track[0]
    source_before = repo.get_episode(episode.episode_id).audio_timeline[0]

    edited = service.update_cue(
        episode_id=episode.episode_id,
        cue_id=cue.cue_id,
        start_seconds=0.6,
        end_seconds=2.7,
        text="Nancy arrives in the village.",
        speaker_label="Narrator",
        approved=True,
    )
    assert edited.source == "creator"
    assert edited.approved is True
    assert edited.text == "Nancy arrives in the village."

    source_after = repo.get_episode(episode.episode_id).audio_timeline[0]
    assert source_after == source_before
    assert service.status_for(
        episode_id=episode.episode_id,
        cue=edited,
    ) == "ready"


def test_srt_export_is_valid_ordered_and_skips_stale_cues(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)
    service = SubtitleTrackService(
        repo,
        project_root=tmp_path / "project",
    )
    built = service.ensure_track(episode.episode_id)
    srt = service.srt_text(episode.episode_id)

    assert srt.startswith(
        "1\n00:00:00,500 --> 00:00:02,500\n"
        "Nancy enters the village."
    )
    assert (
        "2\n00:00:03,000 --> 00:00:04,500\n"
        "Nova notices a light."
    ) in srt

    path = service.export_srt(episode.episode_id)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == srt

    current = repo.get_episode(episode.episode_id)
    current.audio_timeline[0] = current.audio_timeline[0].model_copy(
        update={"text": "Changed source."}
    )
    repo.save_episode(current)
    stale_srt = service.srt_text(episode.episode_id)
    assert "Nancy enters the village." not in stale_srt
    assert "Nova notices a light." in stale_srt

    summary = service.summary(episode.episode_id)
    assert summary.cue_count == 2
    assert summary.ready_count == 1
    assert summary.stale_count == 1


def test_subtitle_track_is_visible_in_episode_creator():
    episodes_ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    subtitle_ui = (
        ROOT / "studio" / "ui" / "creator" / "subtitle_track.py"
    ).read_text(encoding="utf-8")

    assert "render_subtitle_track(" in episodes_ui
    assert "Subtitle Track / 字幕轨" in subtitle_ui
    assert "Generate Subtitles / 生成字幕" in subtitle_ui
    assert "Refresh from Audio / 从对白刷新" in subtitle_ui
    assert "SRT Preview / 字幕文件预览" in subtitle_ui
    assert "Download SRT / 下载字幕" in subtitle_ui
