from __future__ import annotations

import json
from pathlib import Path

import pytest

from studio.models.episode import Episode, Scene, Shot
from studio.models.shot_render import ShotRenderRecord
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.episode_assembly_service import EpisodeAssemblyService


FAKE_MP4 = (
    b"\x00\x00\x00\x18ftypisom"
    b"\x00\x00\x02\x00isomiso2"
    b"\x00\x00\x00\x08free"
)


class FakeShotRenderer:
    def __init__(self, repo, project_root):
        self.repo = repo
        self.project_root = Path(project_root)

    def status_for(self, *, episode_id, scene_id, shot_id):
        episode = self.repo.get_episode(episode_id)
        existing = episode.shot_renders.get(shot_id)
        if existing is not None:
            return existing
        return ShotRenderRecord(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
            source_fingerprint=f"MISSING_{shot_id}",
            storyboard_approval_fingerprint="",
            status="missing",
            video_path=f"renders/{shot_id}.mp4",
            duration_seconds=2.0,
        )

    @staticmethod
    def _valid_mp4(path: Path) -> bool:
        return path.exists() and b"ftyp" in path.read_bytes()[:32]


def _episode(tmp_path, *, include_second=True):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    shots = [
        Shot(
            shot_id="SHOT_01_01",
            scene_id="SCENE_01",
            duration_seconds=2.0,
        ),
        Shot(
            shot_id="SHOT_01_02",
            scene_id="SCENE_01",
            duration_seconds=3.0,
        ),
    ]
    episode = Episode(
        episode_id="EP_ASSEMBLY",
        story_id="STORY_ASSEMBLY",
        title="Assembly Test",
        asset_ids=["CHAR_NANCY", "LOC_WORLD"],
        world_asset_id="LOC_WORLD",
        scenes=[Scene(scene_id="SCENE_01", shots=shots)],
    )
    renders = {
        "SHOT_01_01": ShotRenderRecord(
            episode_id=episode.episode_id,
            scene_id="SCENE_01",
            shot_id="SHOT_01_01",
            source_fingerprint="SRC_1",
            storyboard_approval_fingerprint="APP_1",
            status="rendered",
            video_path=(
                "godot/runtime_state/renders/"
                + episode.episode_id
                + "/SHOT_01_01.mp4"
            ),
            duration_seconds=2.0,
        ),
    }
    if include_second:
        renders["SHOT_01_02"] = ShotRenderRecord(
            episode_id=episode.episode_id,
            scene_id="SCENE_01",
            shot_id="SHOT_01_02",
            source_fingerprint="SRC_2",
            storyboard_approval_fingerprint="APP_2",
            status="rendered",
            video_path=(
                "godot/runtime_state/renders/"
                + episode.episode_id
                + "/SHOT_01_02.mp4"
            ),
            duration_seconds=3.0,
        )
    episode.shot_renders = renders
    repo.save_episode(episode)

    project_root = tmp_path / "project"
    for render in renders.values():
        path = project_root / render.video_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(FAKE_MP4)
    return repo, project_root


def _fake_assembly(clip_paths, output_path):
    assert [path.name for path in clip_paths] == [
        "SHOT_01_01.mp4",
        "SHOT_01_02.mp4",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(FAKE_MP4)


def test_episode_assembly_preserves_shot_order_manifest_and_restart(tmp_path):
    repo, project_root = _episode(tmp_path)
    service = EpisodeAssemblyService(
        repo,
        FakeShotRenderer(repo, project_root),
        assembly_runner=_fake_assembly,
        project_root=project_root,
    )

    record = service.assemble("EP_ASSEMBLY")

    assert record.status == "ready"
    assert record.clip_count == 2
    assert record.total_duration_seconds == 5.0
    assert [clip.shot_id for clip in record.clips] == [
        "SHOT_01_01",
        "SHOT_01_02",
    ]
    assert [clip.start_seconds for clip in record.clips] == [0.0, 2.0]
    assert service.video_bytes(record) == FAKE_MP4

    manifest = json.loads(
        (project_root / record.manifest_path).read_text(encoding="utf-8")
    )
    assert [clip["shot_id"] for clip in manifest["clips"]] == [
        "SHOT_01_01",
        "SHOT_01_02",
    ]
    assert manifest["story_id"] == "STORY_ASSEMBLY"
    assert manifest["world_asset_id"] == "LOC_WORLD"

    restarted = SQLiteStudioRepository(tmp_path / "studio.db")
    service2 = EpisodeAssemblyService(
        restarted,
        FakeShotRenderer(restarted, project_root),
        assembly_runner=_fake_assembly,
        project_root=project_root,
    )
    restored = service2.status_for("EP_ASSEMBLY")
    assert restored.status == "ready"
    assert restored.source_fingerprint == record.source_fingerprint


def test_missing_render_blocks_assembly_without_deleting_valid_clip(tmp_path):
    repo, project_root = _episode(tmp_path, include_second=False)
    first_path = (
        project_root
        / "godot/runtime_state/renders/EP_ASSEMBLY/SHOT_01_01.mp4"
    )
    service = EpisodeAssemblyService(
        repo,
        FakeShotRenderer(repo, project_root),
        assembly_runner=_fake_assembly,
        project_root=project_root,
    )

    with pytest.raises(ValueError, match="SHOT_01_02"):
        service.assemble("EP_ASSEMBLY")

    assert first_path.exists()
    assert first_path.read_bytes() == FAKE_MP4


def test_changed_shot_render_marks_existing_assembly_stale(tmp_path):
    repo, project_root = _episode(tmp_path)
    service = EpisodeAssemblyService(
        repo,
        FakeShotRenderer(repo, project_root),
        assembly_runner=_fake_assembly,
        project_root=project_root,
    )
    ready = service.assemble("EP_ASSEMBLY")
    assert ready.status == "ready"

    episode = repo.get_episode("EP_ASSEMBLY")
    changed = episode.shot_renders["SHOT_01_02"].model_copy(
        update={"source_fingerprint": "SRC_2_CHANGED"}
    )
    episode.shot_renders["SHOT_01_02"] = changed
    repo.save_episode(episode)

    stale = service.status_for("EP_ASSEMBLY")
    assert stale.status == "stale"


def test_episode_assembly_ui_is_visible():
    root = Path(__file__).resolve().parents[1]
    source = (
        root / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "EpisodeAssemblyService" in source
    assert "Assemble Episode / 拼接剧集" in source
    assert "Episode Assembly / 剧集成片" in source
    assert "Download Episode MP4 / 下载剧集" in source
