from __future__ import annotations

import json
from pathlib import Path

import pytest

from studio.models.audio_timeline import EpisodeAudioLine
from studio.models.episode import Episode
from studio.models.episode_assembly import EpisodeAssemblyRecord
from studio.models.story import Story
from studio.core.enums import StoryMode
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.publish_package_service import PublishPackageService


FAKE_MP4 = (
    b"\x00\x00\x00\x18ftypisom"
    b"\x00\x02\x00isomiso2"
    b"\x00\x00\x00\x08free"
)


class FakeAssemblyService:
    def __init__(self, record):
        self.record = record

    def status_for(self, episode_id):
        assert episode_id == self.record.episode_id
        return self.record


def _setup(tmp_path, *, assembly_status="ready"):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    story = Story(
        story_id="STORY_PUBLISH",
        title="Portal Story",
        premise="Nancy and Nova discover a glowing Portal.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=["CHAR_NANCY", "LOC_WORLD"],
    )
    repo.save_story(story)

    episode = Episode(
        episode_id="EP_PUBLISH",
        story_id=story.story_id,
        title="Nancy's Portal Adventure",
        asset_ids=["CHAR_NANCY", "LOC_WORLD"],
        world_asset_id="LOC_WORLD",
        audio_timeline=[
            EpisodeAudioLine(
                line_id="AUD_01",
                scene_id="SCENE_01",
                shot_id="SHOT_01_01",
                speaker_kind="narrator",
                text="Nancy enters the village.",
                start_seconds=0.0,
                duration_seconds=2.0,
                approved=True,
            )
        ],
    )
    repo.save_episode(episode)

    project_root = tmp_path / "project"
    final_video = (
        project_root
        / "godot/runtime_state/episodes/EP_PUBLISH/episode.mp4"
    )
    final_video.parent.mkdir(parents=True, exist_ok=True)
    final_video.write_bytes(FAKE_MP4)

    assembly = EpisodeAssemblyRecord(
        episode_id=episode.episode_id,
        source_fingerprint="ASSEMBLY_V1",
        status=assembly_status,
        video_path=str(final_video.relative_to(project_root)),
        manifest_path=(
            "godot/runtime_state/episodes/EP_PUBLISH/assembly.json"
        ),
        clip_count=2,
        total_duration_seconds=5.0,
    )
    return repo, project_root, assembly


def test_publish_package_requires_current_assembled_video(tmp_path):
    repo, project_root, assembly = _setup(
        tmp_path,
        assembly_status="stale",
    )
    service = PublishPackageService(
        repo,
        FakeAssemblyService(assembly),
        project_root=project_root,
    )

    with pytest.raises(ValueError, match="assembled Episode"):
        service.generate("EP_PUBLISH")


def test_publish_package_generates_files_persists_and_keeps_custom_metadata(tmp_path):
    repo, project_root, assembly = _setup(tmp_path)
    service = PublishPackageService(
        repo,
        FakeAssemblyService(assembly),
        project_root=project_root,
    )

    package = service.generate(
        "EP_PUBLISH",
        title="Nancy & Nova: The First Portal",
        description="A tiny adventure into a brand-new World.",
    )

    assert package.status == "ready"
    assert package.title == "Nancy & Nova: The First Portal"
    assert package.description == "A tiny adventure into a brand-new World."
    assert package.final_video_path == assembly.video_path

    transcript = (
        project_root / package.transcript_path
    ).read_text(encoding="utf-8")
    assert "Nancy enters the village." in transcript

    metadata = json.loads(
        (project_root / package.metadata_path).read_text(encoding="utf-8")
    )
    assert metadata["title"] == package.title
    assert metadata["story_id"] == "STORY_PUBLISH"
    assert metadata["world_asset_id"] == "LOC_WORLD"
    assert metadata["asset_ids"] == ["CHAR_NANCY", "LOC_WORLD"]

    manifest = json.loads(
        (project_root / package.manifest_path).read_text(encoding="utf-8")
    )
    assert manifest["assembly_fingerprint"] == "ASSEMBLY_V1"
    assert manifest["final_video_path"] == assembly.video_path

    saved_episode = repo.get_episode("EP_PUBLISH")
    assert saved_episode.final_package_ready is True
    assert saved_episode.publish_package is not None

    restarted = SQLiteStudioRepository(tmp_path / "studio.db")
    service2 = PublishPackageService(
        restarted,
        FakeAssemblyService(assembly),
        project_root=project_root,
    )
    restored = service2.status_for("EP_PUBLISH")
    assert restored.status == "ready"
    assert restored.title == "Nancy & Nova: The First Portal"
    assert restored.description == "A tiny adventure into a brand-new World."


def test_publish_package_becomes_stale_when_source_changes(tmp_path):
    repo, project_root, assembly = _setup(tmp_path)
    service = PublishPackageService(
        repo,
        FakeAssemblyService(assembly),
        project_root=project_root,
    )
    ready = service.generate("EP_PUBLISH")
    assert ready.status == "ready"

    changed_assembly = assembly.model_copy(
        update={"source_fingerprint": "ASSEMBLY_V2"}
    )
    service_changed = PublishPackageService(
        repo,
        FakeAssemblyService(changed_assembly),
        project_root=project_root,
    )
    stale = service_changed.status_for("EP_PUBLISH")
    assert stale.status == "stale"


def test_publish_package_ui_is_visible():
    root = Path(__file__).resolve().parents[1]
    source = (
        root / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "PublishPackageService" in source
    assert "Publish Package / 发布包" in source
    assert "Generate Publish Package / 生成发布包" in source
    assert "Final MP4 / 成片" in source
    assert "SRT / 字幕" in source
    assert "Transcript / 文稿" in source
    assert "Metadata / 发布信息" in source
