from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.episode import (
    Shot,
    ShotBlockingPoint,
    ShotCameraMotionSpec,
)
from studio.models.world import SpawnPoint, WorldBlueprint, WorldProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.director_shot_session_service import DirectorShotSessionService
from studio.services.episode_service import EpisodeService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService
from studio.storage.local import LocalObjectStorage


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
        display_name="Camera Village",
        slug="camera-village",
        metadata={
            "world_profile": WorldProfile(
                world_name="Camera Village"
            ).model_dump(mode="json"),
            "world_blueprint": WorldBlueprint(
                location_asset_id="TEMP",
                spawn=SpawnPoint(
                    x=0.0,
                    y=0.0,
                    z=34.0,
                    facing_degrees=0.0,
                ),
            ).model_dump(mode="json"),
            "world_creation_complete": True,
        },
    )
    repo.save_asset(character)
    repo.save_asset(world)

    story = StoryService(repo).create_story(
        title="Camera Story",
        premise="Nancy enters and discovers a clue.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives.",
        discovery="Nancy sees a clue.",
        conflict="A gate blocks the path.",
        adventure="Nancy explores.",
        twist="A guardian appears.",
        ending="The Portal opens.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    return character, world, episode


def test_old_shot_without_camera_motion_remains_compatible():
    shot = Shot.model_validate(
        {
            "shot_id": "SHOT_OLD",
            "scene_id": "SCENE_OLD",
            "duration_seconds": 3.0,
        }
    )
    assert shot.camera_motion is None


def test_generated_shots_get_camera_motion_matching_shot_language(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    _character, _world, episode = _episode(repo)
    planned = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )

    establishing = planned.scenes[0].shots[0]
    follow = planned.scenes[0].shots[1]
    reveal = planned.scenes[1].shots[1]
    ending = planned.scenes[-1].shots[-1]

    assert establishing.camera_motion is not None
    assert establishing.camera_motion.movement_mode == "push_in"
    assert establishing.camera_motion.start_fov == 52.0
    assert establishing.camera_motion.end_fov == 44.0
    assert (
        establishing.camera_motion.end_position.z
        < establishing.camera_motion.start_position.z
    )

    assert follow.camera_motion is not None
    assert follow.camera_motion.movement_mode == "follow"
    assert follow.camera_motion.start_position != follow.camera_motion.end_position

    assert reveal.camera_motion is not None
    assert reveal.camera_motion.movement_mode == "reveal"

    assert ending.camera_motion is not None
    assert ending.camera_motion.movement_mode == "pull_back"
    assert ending.camera_motion.end_fov > ending.camera_motion.start_fov


def test_creator_camera_motion_edit_survives_restart_and_migration(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    _character, _world, episode = _episode(repo)
    service = ShotPlanService(repo)
    planned = service.build_for_episode(episode.episode_id)
    shot = planned.scenes[0].shots[0]

    custom = ShotCameraMotionSpec(
        start_position=ShotBlockingPoint(x=10.0, y=5.0, z=20.0),
        end_position=ShotBlockingPoint(x=10.0, y=4.0, z=12.0),
        start_look_at=ShotBlockingPoint(x=0.0, y=1.0, z=20.0),
        end_look_at=ShotBlockingPoint(x=0.0, y=1.0, z=12.0),
        start_fov=60.0,
        end_fov=42.0,
        movement_mode="push_in",
        easing="linear",
        source="creator",
        confidence=1.0,
    )
    edited = service.update_shot(
        episode_id=planned.episode_id,
        scene_id=planned.scenes[0].scene_id,
        shot_id=shot.shot_id,
        duration_seconds=shot.duration_seconds,
        shot_type=shot.shot_type,
        camera=shot.camera,
        action=shot.action,
        expression=shot.expression,
        continuity_notes=shot.continuity_notes,
        blocking=shot.blocking,
        camera_motion=custom,
    )
    saved = edited.scenes[0].shots[0]
    assert saved.camera_motion == custom

    ensured = service.ensure_camera_motion(planned.episode_id)
    assert ensured.scenes[0].shots[0].camera_motion == custom

    restarted = EpisodeService(
        SQLiteStudioRepository(db_path)
    ).get_episode(planned.episode_id)
    assert restarted is not None
    assert restarted.scenes[0].shots[0].camera_motion == custom


def test_director_session_exports_saved_camera_motion(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character, _world, episode = _episode(repo)
    episode = ShotPlanService(repo).build_for_episode(episode.episode_id)
    shot = episode.scenes[0].shots[0]
    assert shot.camera_motion is not None

    session = DirectorShotSessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        export_path=tmp_path / "director.json",
    ).build(
        episode_id=episode.episode_id,
        scene_id=episode.scenes[0].scene_id,
        shot_id=shot.shot_id,
    )

    motion = shot.camera_motion
    assert session.character_asset_id == character.asset_id
    assert session.camera.position == (
        motion.start_position.x,
        motion.start_position.y,
        motion.start_position.z,
    )
    assert session.camera.end_position == (
        motion.end_position.x,
        motion.end_position.y,
        motion.end_position.z,
    )
    assert session.camera.end_fov == motion.end_fov
    assert session.camera.movement_mode == motion.movement_mode
    assert session.camera.easing == motion.easing


def test_episode_ui_exposes_camera_motion_editor():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "Camera Motion / 镜头运动" in ui
    assert "Motion Mode / 运动方式" in ui
    assert '"Cam Start X"' in ui
    assert '"Cam End X"' in ui
    assert '"Look Start X"' in ui
    assert '"Look End X"' in ui
    assert '"Start FOV"' in ui
    assert '"End FOV"' in ui
    assert "shot_service.ensure_camera_motion" in ui
