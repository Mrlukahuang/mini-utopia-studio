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
from studio.services.production_status_service import (
    EpisodeProductionStatusService,
)
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService
from studio.services.storyboard_service import StoryboardService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def _services(tmp_path, *, with_scenes=False, with_shots=False):
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
        title="Production Adventure",
        premise="Nancy and Nova make a tiny movie.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy enters the village.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    if with_scenes:
        episode = SceneBreakdownService(repo).build_from_story(
            episode.episode_id
        )
    if with_shots:
        episode = ShotPlanService(repo).build_for_episode(
            episode.episode_id
        )

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
        project_root=tmp_path / "project",
    )
    status = EpisodeProductionStatusService(repo, storyboard)
    return repo, episode, status


def test_new_episode_points_to_scene_breakdown(tmp_path):
    _repo, episode, status_service = _services(tmp_path)
    status = status_service.status(episode.episode_id)

    assert status.story_ready is True
    assert status.scenes_total == 0
    assert status.shots_total == 0
    assert status.next_action == "build_scenes"
    assert 0 < status.progress_percent < 100


def test_scene_only_episode_points_to_shot_list(tmp_path):
    _repo, episode, status_service = _services(
        tmp_path,
        with_scenes=True,
    )
    status = status_service.status(episode.episode_id)

    assert status.scenes_total == 1
    assert status.scenes_ready == 1
    assert status.shots_total == 0
    assert status.next_action == "build_shots"


def test_planned_episode_points_to_storyboard_and_uses_real_shot_contract(tmp_path):
    _repo, episode, status_service = _services(
        tmp_path,
        with_scenes=True,
        with_shots=True,
    )
    status = status_service.status(episode.episode_id)

    assert status.shots_total == 2
    assert status.shots_ready == 2
    assert status.storyboard_ready == 0
    assert status.storyboard_approved == 0
    assert status.next_action == "generate_storyboard"


def test_ready_and_approved_storyboards_drive_next_action_and_restart(tmp_path):
    repo, episode, status_service = _services(
        tmp_path,
        with_scenes=True,
        with_shots=True,
    )
    for scene in episode.scenes:
        for shot in scene.shots:
            session = status_service.storyboard.director.build(
                episode_id=episode.episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            from studio.models.storyboard import StoryboardFrameRecord
            frame = StoryboardFrameRecord(
                episode_id=episode.episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
                source_fingerprint=session.source_fingerprint,
                status="ready",
                frame_path=(
                    f"godot/runtime_state/storyboards/"
                    f"{episode.episode_id}/{shot.shot_id}.png"
                ),
                capture_time_seconds=shot.duration_seconds * 0.5,
                review_status="approved",
                review_source_fingerprint=session.source_fingerprint,
            )
            episode.storyboard_frames[shot.shot_id] = frame
    repo.save_episode(episode)

    # status_for checks image existence before keeping ready; use current
    # fingerprints with tiny PNG files to model approved production output.
    png = b"\x89PNG\r\n\x1a\nrest"
    for frame in episode.storyboard_frames.values():
        path = tmp_path / "project" / frame.frame_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)

    approved = status_service.status(episode.episode_id)
    assert approved.storyboard_ready == approved.shots_total
    assert approved.storyboard_approved == approved.shots_total
    assert approved.next_action == "render_shots"

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
    restarted_status = EpisodeProductionStatusService(
        restarted,
        StoryboardService(
            restarted,
            director,
            project_root=tmp_path / "project",
        ),
    ).status(episode.episode_id)
    assert restarted_status.storyboard_approved == approved.shots_total
    assert restarted_status.next_action == "render_shots"


def test_stale_storyboard_lowers_current_approval_count(tmp_path):
    repo, episode, status_service = _services(
        tmp_path,
        with_scenes=True,
        with_shots=True,
    )
    scene = episode.scenes[0]
    shot = scene.shots[0]
    session = status_service.storyboard.director.build(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
    )
    from studio.models.storyboard import StoryboardFrameRecord
    frame = StoryboardFrameRecord(
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        shot_id=shot.shot_id,
        source_fingerprint=session.source_fingerprint,
        status="ready",
        frame_path=(
            f"godot/runtime_state/storyboards/"
            f"{episode.episode_id}/{shot.shot_id}.png"
        ),
        capture_time_seconds=1.0,
        review_status="approved",
        review_source_fingerprint=session.source_fingerprint,
    )
    episode.storyboard_frames[shot.shot_id] = frame
    repo.save_episode(episode)
    path = tmp_path / "project" / frame.frame_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\nrest")

    current = repo.get_episode(episode.episode_id)
    current.scenes[0].shots[0] = current.scenes[0].shots[0].model_copy(
        update={"action": "Nancy changes direction."}
    )
    repo.save_episode(current)

    status = status_service.status(episode.episode_id)
    assert status.storyboard_stale == 1
    assert status.storyboard_approved == 0
    assert status.next_action == "generate_storyboard"


def test_production_progress_ui_is_child_visible():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")
    assert "Production Progress / 制作进度" in ui
    assert "Generate Next Frame / 生成下一张分镜" in ui
    assert "Storyboard Approved · Ready to Render" in ui
    assert "production_status_service.status(" in ui
    loading = "Loading Production Progress / 正在读取制作进度…"
    assert loading in ui
    assert "production_progress_slot = st.empty()" in ui
    assert ui.index(loading) < ui.index(
        "production_status_service.status("
    )
