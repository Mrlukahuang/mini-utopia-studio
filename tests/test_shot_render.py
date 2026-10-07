from __future__ import annotations

import base64
from pathlib import Path

import pytest

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.episode import Episode
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)
from studio.services.episode_service import EpisodeService
from studio.services.equipment_service import EquipmentService
from studio.services.production_status_service import (
    EpisodeProductionStatusService,
)
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.shot_render_service import ShotRenderService
from studio.services.story_service import StoryService
from studio.services.storyboard_service import StoryboardService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl0sRoAAAAASUVORK5CYII="
)
FAKE_MP4 = (
    b"\x00\x00\x00\x18ftypisom"
    b"\x00\x00\x02\x00isomiso2"
    b"\x00\x00\x00\x08free"
)


def _setup(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
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
    BabyService(repo).create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    EquipmentService(repo).ensure_starter_collection()

    story = StoryService(repo).create_story(
        title="Render Adventure",
        premise="Nancy walks through the village.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy enters the village.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    episode = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )

    project_root = tmp_path / "project"
    (project_root / "godot" / "runtime_state").mkdir(parents=True)

    director = DirectorShotSessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        equipment=EquipmentService(repo),
        babies=BabyService(repo),
        export_path=tmp_path / "director.json",
    )
    storyboard = StoryboardService(
        repo,
        director,
        project_root=project_root,
    )
    scene = episode.scenes[0]
    shot = scene.shots[0]
    session = director.build(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    frame_path = (
        project_root
        / "godot"
        / "runtime_state"
        / "storyboards"
        / episode.episode_id
        / f"{shot.shot_id}.png"
    )
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    frame_path.write_bytes(PNG_1X1)

    from studio.models.storyboard import StoryboardFrameRecord

    frame = StoryboardFrameRecord(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        source_fingerprint=session.source_fingerprint,
        status="ready",
        frame_path=str(frame_path.relative_to(project_root)),
        capture_time_seconds=shot.duration_seconds * 0.5,
        review_status="approved",
        review_source_fingerprint=session.source_fingerprint,
    )
    episode.storyboard_frames[shot.shot_id] = frame
    repo.save_episode(episode)
    return repo, director, storyboard, episode, scene, shot, project_root


def _fake_render(_request_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(FAKE_MP4)


def test_old_episode_payload_defaults_to_empty_shot_renders():
    episode = Episode.model_validate(
        {
            "episode_id": "EP_OLD",
            "story_id": "STORY_OLD",
            "title": "Old Episode",
        }
    )
    assert episode.shot_renders == {}


def test_approved_shot_renders_and_receipt_survives_restart(tmp_path):
    (
        repo,
        director,
        storyboard,
        episode,
        scene,
        shot,
        project_root,
    ) = _setup(tmp_path)

    renderer = ShotRenderService(
        repo,
        director,
        storyboard,
        render_runner=_fake_render,
        project_root=project_root,
        fps=24,
    )
    before = renderer.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert before.status == "missing"

    rendered = renderer.render_shot(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert rendered.status == "rendered"
    assert rendered.frame_count == round(shot.duration_seconds * 24)
    assert rendered.source_fingerprint
    assert rendered.storyboard_approval_fingerprint
    assert renderer.video_bytes(rendered) == FAKE_MP4

    restarted = SQLiteStudioRepository(tmp_path / "studio.db")
    director2 = DirectorShotSessionService(
        restarted,
        CharacterRuntimeService(
            restarted,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        equipment=EquipmentService(restarted),
        babies=BabyService(restarted),
        export_path=tmp_path / "director2.json",
    )
    storyboard2 = StoryboardService(
        restarted,
        director2,
        project_root=project_root,
    )
    renderer2 = ShotRenderService(
        restarted,
        director2,
        storyboard2,
        render_runner=_fake_render,
        project_root=project_root,
    )
    restored = renderer2.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert restored.status == "rendered"
    assert restored.generated_at is not None


def test_unapproved_or_stale_storyboard_blocks_render(tmp_path):
    repo, director, storyboard, episode, scene, shot, project_root = _setup(
        tmp_path
    )
    current = repo.get_episode(episode.episode_id)
    frame = current.storyboard_frames[shot.shot_id]
    current.storyboard_frames[shot.shot_id] = frame.model_copy(
        update={
            "review_status": "unreviewed",
            "review_source_fingerprint": "",
        }
    )
    repo.save_episode(current)

    renderer = ShotRenderService(
        repo,
        director,
        storyboard,
        render_runner=_fake_render,
        project_root=project_root,
    )
    with pytest.raises(ValueError, match="Approved"):
        renderer.render_shot(
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            shot_id=shot.shot_id,
        )


def test_shot_change_marks_existing_video_stale_and_production_count_drops(tmp_path):
    repo, director, storyboard, episode, scene, shot, project_root = _setup(
        tmp_path
    )
    renderer = ShotRenderService(
        repo,
        director,
        storyboard,
        render_runner=_fake_render,
        project_root=project_root,
    )
    renderer.render_shot(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )

    current = repo.get_episode(episode.episode_id)
    current.scenes[0].shots[0] = current.scenes[0].shots[0].model_copy(
        update={"action": "Nancy turns toward the Portal."}
    )
    repo.save_episode(current)

    stale = renderer.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert stale.status == "stale"

    production = EpisodeProductionStatusService(
        repo,
        storyboard,
        shot_renderer=renderer,
    ).status(episode.episode_id)
    assert production.rendered_shots == 0


def test_render_ui_and_godot_frame_capture_contract_exist():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    capture = (
        ROOT / "godot" / "scripts" / "shot_frame_capture.gd"
    ).read_text(encoding="utf-8")

    assert "Render Shot / 渲染镜头" in ui
    assert "Download Shot MP4 / 下载镜头" in ui
    assert "shot_render_service.render_shot(" in ui
    assert "frame_%05d.png" in capture
    assert "runtime.advance_shot(frame_delta)" in capture
    assert "MEDIA-02A Shot capture: PASS" in capture
