from __future__ import annotations

import base64
import json
from pathlib import Path

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
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService
from studio.services.storyboard_service import StoryboardService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl0sRoAAAAASUVORK5CYII="
)


def _setup(repo: SQLiteStudioRepository):
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
        title="Storyboard Adventure",
        premise="Nancy and Nova enter the village.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy and Nova walk into the village square.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    episode = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )
    return character, world, episode


def _director(repo, root: Path):
    return DirectorShotSessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(root / "storage"),
        ),
        equipment=EquipmentService(repo),
        babies=BabyService(repo),
        export_path=root / "director.json",
    )


def _fake_capture(request_path: Path) -> None:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    output = str(request["output_path"])
    assert output.startswith("res://")
    project_root = request_path.parents[2]
    target = project_root / "godot" / output.removeprefix("res://")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(PNG_1X1)


def test_old_episode_payload_defaults_to_empty_storyboard():
    episode = Episode.model_validate(
        {
            "episode_id": "EP_OLD",
            "story_id": "STORY_OLD",
            "title": "Old Episode",
        }
    )
    assert episode.storyboard_frames == {}


def test_storyboard_frame_is_deterministic_ready_and_persistent(tmp_path):
    project_root = tmp_path / "project"
    (project_root / "godot" / "runtime_state").mkdir(parents=True)
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    _character, _world, episode = _setup(repo)
    scene = episode.scenes[0]
    shot = scene.shots[0]

    storyboard = StoryboardService(
        repo,
        _director(repo, tmp_path),
        capture_runner=_fake_capture,
        project_root=project_root,
    )

    missing = storyboard.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert missing.status == "missing"
    assert missing.capture_time_seconds == shot.duration_seconds * 0.5

    ready = storyboard.generate_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert ready.status == "ready"
    assert ready.generated_at is not None
    assert ready.source_fingerprint
    assert ready.camera_summary
    assert storyboard.frame_bytes(ready) == PNG_1X1

    restarted_repo = SQLiteStudioRepository(db_path)
    restarted = StoryboardService(
        restarted_repo,
        _director(restarted_repo, tmp_path),
        capture_runner=_fake_capture,
        project_root=project_root,
    )
    persisted = restarted.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert persisted.status == "ready"
    assert persisted.source_fingerprint == ready.source_fingerprint


def test_storyboard_marks_old_frame_stale_when_source_shot_changes(tmp_path):
    project_root = tmp_path / "project"
    (project_root / "godot" / "runtime_state").mkdir(parents=True)
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _character, _world, episode = _setup(repo)
    scene = episode.scenes[0]
    shot = scene.shots[0]

    storyboard = StoryboardService(
        repo,
        _director(repo, tmp_path),
        capture_runner=_fake_capture,
        project_root=project_root,
    )
    ready = storyboard.generate_frame(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert ready.status == "ready"

    current = repo.get_episode(episode.episode_id)
    assert current is not None
    changed_scene = current.scenes[0]
    changed_scene.shots[0] = changed_scene.shots[0].model_copy(
        update={"action": "Nancy suddenly turns toward the Portal."}
    )
    repo.save_episode(current)

    stale = storyboard.status_for(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    assert stale.status == "stale"
    assert stale.source_fingerprint == ready.source_fingerprint


def test_storyboard_creator_ui_and_godot_capture_contract_exist():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    capture = (
        ROOT / "godot" / "scripts" / "storyboard_capture.gd"
    ).read_text(encoding="utf-8")

    assert "Storyboard / 分镜板" in ui
    assert "Generate Frame / 生成分镜" in ui
    assert "Refresh Frame / 更新分镜" in ui
    assert "storyboard_service.status_for(" in ui
    assert "storyboard_service.generate_frame(" in ui
    assert "capture_time_seconds" in capture
    assert "root.get_texture().get_image()" in capture
    assert "save_png" in capture
