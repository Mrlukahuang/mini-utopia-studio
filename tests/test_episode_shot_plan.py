from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.episode_service import EpisodeService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.story_service import StoryService


ROOT = Path(__file__).resolve().parents[1]


def _production_episode(repo: SQLiteStudioRepository):
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

    story = StoryService(repo).create_story(
        title="Portal Adventure",
        premise="Nancy follows a Portal mystery.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy arrives.",
        discovery="Nancy finds a clue.",
        conflict="A gate blocks the way.",
        adventure="Nancy solves the gate puzzle.",
        twist="A friendly guardian appears.",
        ending="The Portal opens.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    return SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )


def test_scene_breakdown_builds_stable_two_shot_camera_rhythm(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    episode = _production_episode(repo)

    planned = ShotPlanService(repo).build_for_episode(episode.episode_id)

    assert len(planned.scenes) == 6
    assert [len(scene.shots) for scene in planned.scenes] == [2] * 6
    assert planned.scenes[0].shots[0].shot_id == "SHOT_01_01"
    assert planned.scenes[0].shots[1].shot_id == "SHOT_01_02"
    assert planned.scenes[-1].shots[-1].shot_id == "SHOT_06_02"

    arrive = planned.scenes[0].shots
    assert arrive[0].shot_type == "Establishing"
    assert "Wide establishing" in arrive[0].camera
    assert arrive[1].shot_type == "Follow"

    portal = planned.scenes[-1].shots
    assert portal[0].shot_type == "Portal Reveal"
    assert portal[1].shot_type == "Ending"

    for scene in planned.scenes:
        for shot in scene.shots:
            assert shot.scene_id == scene.scene_id
            assert shot.asset_ids == scene.asset_ids
            assert shot.action
            assert shot.camera
            assert shot.continuity_notes

    assert ShotPlanService.total_duration(planned) > 30.0


def test_shot_edit_survives_restart_and_existing_plan_is_not_rebuilt_implicitly(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    episode = _production_episode(repo)
    service = ShotPlanService(repo)
    planned = service.build_for_episode(episode.episode_id)

    edited = service.update_shot(
        episode_id=planned.episode_id,
        scene_id="SCENE_01",
        shot_id="SHOT_01_01",
        duration_seconds=6.5,
        shot_type="Hero Establishing",
        camera="Low wide · slow crane down",
        action="Nancy and Nova enter through the village arch.",
        expression="wonder",
        continuity_notes=["Crown on.", "Nova camera-left."],
    )
    assert edited.scenes[0].shots[0].duration_seconds == 6.5

    unchanged = service.build_for_episode(planned.episode_id)
    assert unchanged.scenes[0].shots[0].shot_type == "Hero Establishing"

    restarted_repo = SQLiteStudioRepository(db_path)
    restarted = EpisodeService(restarted_repo).get_episode(planned.episode_id)
    assert restarted is not None
    shot = restarted.scenes[0].shots[0]
    assert shot.duration_seconds == 6.5
    assert shot.camera == "Low wide · slow crane down"
    assert shot.continuity_notes == ["Crown on.", "Nova camera-left."]

    rebuilt = ShotPlanService(restarted_repo).build_for_episode(
        planned.episode_id,
        replace=True,
    )
    assert rebuilt.scenes[0].shots[0].shot_type == "Establishing"
    assert rebuilt.scenes[0].shots[0].duration_seconds == 4.0


def test_episode_page_exposes_total_duration_shot_build_edit_and_confirmed_rebuild():
    ui = (
        ROOT / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "Build Shot List / 生成镜头表" in ui
    assert "Rebuild Shot List / 重建镜头表" in ui
    assert "重建会覆盖 Shot 编辑" in ui
    assert "Shot List / 镜头表" in ui
    assert "Duration / 时长（秒）" in ui
    assert "Camera / 机位与运动" in ui
    assert "Save Shot / 保存镜头" in ui
    assert "shot_service.total_duration(episode)" in ui
    assert "shot_service.update_shot(" in ui
