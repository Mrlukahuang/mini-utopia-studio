from pathlib import Path
from types import SimpleNamespace

from studio.models.episode import Episode, Scene, Shot
from studio.models.shot_render import ShotRenderRecord
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.episode_batch_render_service import (
    EpisodeBatchRenderService,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeStoryboard:
    def __init__(self, approved_ids):
        self.approved_ids = set(approved_ids)

    def status_for(self, *, episode_id, scene_id, shot_id):
        return SimpleNamespace(
            approved_current=shot_id in self.approved_ids
        )


class FakeRenderer:
    def __init__(self, statuses, fail_ids=()):
        self.statuses = dict(statuses)
        self.fail_ids = set(fail_ids)
        self.render_calls = []

    def status_for(self, *, episode_id, scene_id, shot_id):
        status = self.statuses.get(shot_id, "missing")
        return ShotRenderRecord(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
            source_fingerprint=f"SRC_{shot_id}",
            storyboard_approval_fingerprint=f"APP_{shot_id}",
            status=status,
            video_path=f"renders/{shot_id}.mp4",
            duration_seconds=2.0,
        )

    def render_shot(self, *, episode_id, scene_id, shot_id):
        self.render_calls.append(shot_id)
        status = "failed" if shot_id in self.fail_ids else "rendered"
        self.statuses[shot_id] = status
        return self.status_for(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )


def _episode():
    return Episode(
        episode_id="EP_BATCH",
        story_id="STORY_BATCH",
        title="Batch Render",
        scenes=[
            Scene(
                scene_id="SCENE_01",
                shots=[
                    Shot(
                        shot_id="SHOT_01_01",
                        scene_id="SCENE_01",
                    ),
                    Shot(
                        shot_id="SHOT_01_02",
                        scene_id="SCENE_01",
                    ),
                    Shot(
                        shot_id="SHOT_01_03",
                        scene_id="SCENE_01",
                    ),
                ],
            )
        ],
    )


def test_batch_render_skips_existing_and_unapproved_shots(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    repo.save_episode(_episode())

    renderer = FakeRenderer(
        {
            "SHOT_01_01": "rendered",
            "SHOT_01_02": "missing",
            "SHOT_01_03": "missing",
        }
    )
    service = EpisodeBatchRenderService(
        repo,
        FakeStoryboard({"SHOT_01_01", "SHOT_01_02"}),
        renderer,
    )

    result = service.render_episode("EP_BATCH")

    assert result.total_shots == 3
    assert result.eligible_shots == 2
    assert result.already_rendered == 1
    assert result.rendered_now == 1
    assert result.blocked_shots == ["SHOT_01_03"]
    assert result.failed_shots == []
    assert renderer.render_calls == ["SHOT_01_02"]
    assert result.complete is False


def test_batch_render_failure_can_retry_only_failed_shot(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    repo.save_episode(_episode())
    approved = {"SHOT_01_01", "SHOT_01_02", "SHOT_01_03"}

    renderer = FakeRenderer(
        {
            "SHOT_01_01": "rendered",
            "SHOT_01_02": "missing",
            "SHOT_01_03": "rendered",
        },
        fail_ids={"SHOT_01_02"},
    )
    service = EpisodeBatchRenderService(
        repo,
        FakeStoryboard(approved),
        renderer,
    )
    first = service.render_episode("EP_BATCH")

    assert first.failed_shots == ["SHOT_01_02"]
    assert first.already_rendered == 2
    assert renderer.render_calls == ["SHOT_01_02"]

    renderer.fail_ids.clear()
    renderer.render_calls.clear()
    second = service.render_episode("EP_BATCH")

    assert second.failed_shots == []
    assert second.rendered_now == 1
    assert second.already_rendered == 2
    assert second.complete is True
    assert renderer.render_calls == ["SHOT_01_02"]


def test_batch_render_ui_is_visible():
    source = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "EpisodeBatchRenderService" in source
    assert "Render Approved Episode / 批量渲染已批准镜头" in source
    assert "已完成镜头不会重复渲染" in source
    assert "batch_render_service.render_episode(" in source
