from __future__ import annotations

import base64
import json
from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)
from studio.services.episode_service import EpisodeService
from studio.services.equipment_service import EquipmentService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService
from studio.services.storyboard_service import StoryboardService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl0sRoAAAAASUVORK5CYII="
)


def _capture(request_path: Path) -> None:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    project_root = request_path.parents[2]
    output = str(request["output_path"]).removeprefix("res://")
    target = project_root / "godot" / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(PNG_1X1)


def _setup(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
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
        title="Review Storyboard",
        premise="Nancy enters the village.",
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
        capture_runner=_capture,
        project_root=project_root,
    )
    return repo, storyboard, episode, project_root


def test_storyboard_approval_and_needs_change_persist(tmp_path):
    repo, storyboard, episode, project_root = _setup(tmp_path)
    scene = episode.scenes[0]
    shot = scene.shots[0]
    ready = storyboard.generate_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert ready.status == "ready"

    approved = storyboard.review_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        review_status="approved",
        note="Framing looks good.",
    )
    assert approved.approved_current is True
    assert approved.review_note == "Framing looks good."
    assert approved.review_source_fingerprint == approved.source_fingerprint

    restarted = SQLiteStudioRepository(tmp_path / "studio.db")
    director = DirectorShotSessionService(
        restarted,
        CharacterRuntimeService(
            restarted,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        equipment=EquipmentService(restarted),
        babies=BabyService(restarted),
        export_path=tmp_path / "director2.json",
    )
    restored = StoryboardService(
        restarted,
        director,
        capture_runner=_capture,
        project_root=project_root,
    ).status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert restored.approved_current is True
    assert restored.reviewed_at is not None

    changed = StoryboardService(
        restarted,
        director,
        capture_runner=_capture,
        project_root=project_root,
    ).review_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        review_status="needs_change",
        note="Move camera closer.",
    )
    assert changed.review_status == "needs_change"
    assert changed.approved_current is False
    assert changed.review_note == "Move camera closer."


def test_source_change_invalidates_prior_approval_and_refresh_resets_review(tmp_path):
    repo, storyboard, episode, _project_root = _setup(tmp_path)
    scene = episode.scenes[0]
    shot = scene.shots[0]
    storyboard.generate_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    storyboard.review_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        review_status="approved",
    )

    current = repo.get_episode(episode.episode_id)
    assert current is not None
    current.scenes[0].shots[0] = current.scenes[0].shots[0].model_copy(
        update={"action": "Nancy turns toward a new clue."}
    )
    repo.save_episode(current)

    stale = storyboard.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert stale.status == "stale"
    assert stale.review_status == "approved"
    assert stale.approved_current is False

    refreshed = storyboard.generate_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert refreshed.status == "ready"
    assert refreshed.review_status == "unreviewed"
    assert refreshed.review_source_fingerprint == ""
    assert refreshed.reviewed_at is None


def test_storyboard_review_ui_is_visible():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    assert "Approve / 批准" in ui
    assert "Needs Change / 需修改" in ui
    assert "Review Note / 审核备注" in ui
    assert "Approved" in ui
    assert "storyboard_service.review_frame(" in ui
