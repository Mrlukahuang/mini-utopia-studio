from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.episode import PerformanceCue, Shot
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
        display_name="Performance Village",
        slug="performance-village",
        metadata={
            "world_profile": WorldProfile(
                world_name="Performance Village"
            ).model_dump(mode="json"),
            "world_blueprint": WorldBlueprint(
                location_asset_id="TEMP",
                spawn=SpawnPoint(x=0.0, y=0.0, z=34.0),
            ).model_dump(mode="json"),
            "world_creation_complete": True,
        },
    )
    repo.save_asset(character)
    repo.save_asset(world)

    story = StoryService(repo).create_story(
        title="Performance Story",
        premise="Nancy discovers a surprising Portal clue.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy walks into the village.",
        discovery="Nancy discovers a glowing clue.",
        conflict="Nancy reacts to a surprising blocked gate.",
        adventure="Nancy explores the route.",
        twist="A surprising guardian appears.",
        ending="Nancy looks toward the Portal.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    return episode


def test_old_shot_without_performance_cues_remains_compatible():
    shot = Shot.model_validate(
        {
            "shot_id": "SHOT_OLD",
            "scene_id": "SCENE_OLD",
            "duration_seconds": 3.0,
        }
    )
    assert shot.performance_cues is None


def test_generated_shots_receive_ordered_performance_cues(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _episode(repo)
    planned = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )

    arrive = planned.scenes[0].shots[0]
    assert arrive.performance_cues is not None
    assert any(
        cue.cue_type == "walk"
        for cue in arrive.performance_cues
    )

    discover = planned.scenes[1].shots[1]
    assert discover.performance_cues is not None
    cue_types = [cue.cue_type for cue in discover.performance_cues]
    assert "reaction" in cue_types
    assert "look_at" in cue_types
    assert [cue.start_seconds for cue in discover.performance_cues] == sorted(
        cue.start_seconds for cue in discover.performance_cues
    )

    portal = planned.scenes[-1].shots[0]
    assert portal.performance_cues is not None
    assert any(cue.cue_type == "look_at" for cue in portal.performance_cues)


def test_creator_performance_cue_edit_persists_and_ensure_does_not_overwrite(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    episode = _episode(repo)
    service = ShotPlanService(repo)
    planned = service.build_for_episode(episode.episode_id)
    shot = planned.scenes[0].shots[0]

    custom = [
        PerformanceCue(
            cue_id=f"{shot.shot_id}_CUSTOM",
            cue_type="celebrate",
            start_seconds=1.1,
            duration_seconds=0.8,
            intensity=0.92,
            source="creator",
            confidence=1.0,
        )
    ]
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
        camera_motion=shot.camera_motion,
        performance_cues=custom,
    )
    assert edited.scenes[0].shots[0].performance_cues == custom

    ensured = service.ensure_performance_cues(planned.episode_id)
    assert ensured.scenes[0].shots[0].performance_cues == custom

    restarted = EpisodeService(
        SQLiteStudioRepository(db_path)
    ).get_episode(planned.episode_id)
    assert restarted is not None
    assert restarted.scenes[0].shots[0].performance_cues == custom


def test_episode_ui_exposes_performance_cue_timing_type_and_intensity():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "Performance Cues / 表演提示" in ui
    assert '"Cue Type"' in ui
    assert '"Start (s)"' in ui
    assert '"Cue Duration"' in ui
    assert '"Intensity"' in ui
    assert "shot_service.ensure_performance_cues" in ui
