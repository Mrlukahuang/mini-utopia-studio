from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.episode import (
    Shot,
    ShotBlockingPoint,
    ShotBlockingSpec,
)
from studio.models.world import SpawnPoint, WorldBlueprint, WorldProfile
from studio.repositories.sqlite import SQLiteStudioRepository
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
        display_name="Blocking Village",
        slug="blocking-village",
        metadata={
            "world_profile": WorldProfile(
                world_name="Blocking Village"
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
        title="Blocking Story",
        premise="Nancy walks through the village.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives.",
        discovery="Nancy sees a clue.",
        conflict="A gate blocks the road.",
        adventure="Nancy explores.",
        twist="A guardian appears.",
        ending="The Portal opens.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    return SceneBreakdownService(repo).build_from_story(episode.episode_id)


def test_old_shot_payload_without_blocking_remains_compatible():
    shot = Shot.model_validate(
        {
            "shot_id": "SHOT_OLD",
            "scene_id": "SCENE_OLD",
            "duration_seconds": 3.0,
        }
    )
    assert shot.blocking is None


def test_generated_shots_receive_deterministic_world_relative_blocking(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)

    planned = ShotPlanService(repo).build_for_episode(episode.episode_id)
    arrive = planned.scenes[0].shots[0]
    follow = planned.scenes[0].shots[1]

    assert arrive.blocking is not None
    assert arrive.blocking.actor_start == ShotBlockingPoint(
        x=0.0,
        y=0.0,
        z=34.0,
    )
    assert arrive.blocking.actor_end == ShotBlockingPoint(
        x=0.0,
        y=0.0,
        z=29.0,
    )
    assert arrive.blocking.facing_degrees == 0.0
    assert arrive.blocking.movement_style == "walk"
    assert arrive.blocking.source == "generated"

    assert follow.blocking is not None
    assert follow.blocking.actor_start.z == 29.0
    assert follow.blocking.actor_end.z == 26.0
    assert follow.blocking.movement_style == "walk"


def test_creator_blocking_edit_persists_and_is_not_overwritten_by_ensure(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    episode = _episode(repo)
    service = ShotPlanService(repo)
    planned = service.build_for_episode(episode.episode_id)
    shot = planned.scenes[0].shots[0]

    custom = ShotBlockingSpec(
        actor_start=ShotBlockingPoint(x=2.0, y=0.0, z=20.0),
        actor_end=ShotBlockingPoint(x=4.0, y=0.0, z=12.0),
        facing_degrees=14.0,
        baby_offset=ShotBlockingPoint(x=-1.2, y=0.0, z=1.4),
        movement_style="run",
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
        blocking=custom,
    )
    saved = edited.scenes[0].shots[0]
    assert saved.blocking is not None
    assert saved.blocking.source == "creator"
    assert saved.blocking.actor_end.z == 12.0
    assert saved.blocking.movement_style == "run"

    ensured = service.ensure_blocking(planned.episode_id)
    assert ensured.scenes[0].shots[0].blocking == saved.blocking

    restarted = EpisodeService(
        SQLiteStudioRepository(db_path)
    ).get_episode(planned.episode_id)
    assert restarted is not None
    assert restarted.scenes[0].shots[0].blocking == saved.blocking


def test_ensure_blocking_migrates_legacy_shots_without_rebuilding_edits(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)
    service = ShotPlanService(repo)
    planned = service.build_for_episode(episode.episode_id)

    first = planned.scenes[0].shots[0].model_copy(
        update={
            "camera": "Creator custom camera",
            "blocking": None,
        }
    )
    planned.scenes[0] = planned.scenes[0].model_copy(
        update={
            "shots": [
                first,
                *planned.scenes[0].shots[1:],
            ]
        }
    )
    repo.save_episode(planned)

    migrated = service.ensure_blocking(planned.episode_id)
    migrated_shot = migrated.scenes[0].shots[0]
    assert migrated_shot.camera == "Creator custom camera"
    assert migrated_shot.blocking is not None
    assert migrated_shot.blocking.source == "generated"


def test_episode_ui_exposes_editable_blocking_fields():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "Blocking / 角色走位" in ui
    assert '"Start X"' in ui
    assert '"End X"' in ui
    assert "Facing / 朝向（°）" in ui
    assert "Movement / 走位方式" in ui
    assert "Baby Offset X" in ui
    assert "shot_service.ensure_blocking" in ui
