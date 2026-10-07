from __future__ import annotations

import base64
import json
from pathlib import Path

from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.storyboard import StoryboardFrameRecord
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)
from studio.services.episode_assembly_service import EpisodeAssemblyService
from studio.services.episode_service import EpisodeService
from studio.services.equipment_service import EquipmentService
from studio.services.production_status_service import (
    EpisodeProductionStatusService,
)
from studio.services.publish_package_service import PublishPackageService
from studio.services.scene_breakdown_service import SceneBreakdownService
from studio.services.shot_plan_service import ShotPlanService
from studio.services.shot_render_service import ShotRenderService
from studio.services.story_service import StoryService
from studio.services.storyboard_service import StoryboardService
from studio.storage.local import LocalObjectStorage


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl0sRoAAAAASUVORK5CYII="
)
FAKE_MP4 = (
    b"\x00\x00\x00\x18ftypisom"
    b"\x00\x00\x02\x00isomiso2"
    b"\x00\x00\x00\x08free"
)


def _fake_video(_inputs, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(FAKE_MP4)


def _fake_shot(_request_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(FAKE_MP4)


def _runtime_services(repo, tmp_path):
    project_root = tmp_path / "project"
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
    renderer = ShotRenderService(
        repo,
        director,
        storyboard,
        render_runner=_fake_shot,
        project_root=project_root,
    )
    assembly = EpisodeAssemblyService(
        repo,
        renderer,
        assembly_runner=_fake_video,
        project_root=project_root,
    )
    package = PublishPackageService(
        repo,
        assembly,
        project_root=project_root,
    )
    production = EpisodeProductionStatusService(
        repo,
        storyboard,
        shot_renderer=renderer,
        assembly_service=assembly,
        publish_package_service=package,
    )
    return project_root, director, storyboard, renderer, assembly, package, production


def test_first_production_loop_closes_survives_restart_and_goes_stale_on_shot_change(
    tmp_path,
):
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
        display_name="Nova star",
        species_id="star_baby",
    )
    EquipmentService(repo).ensure_starter_collection()

    original_asset_ids = {
        asset.asset_id
        for asset in repo.list_assets()
    }

    story = StoryService(repo).create_story(
        title="Nancy's First Production Adventure",
        premise="Nancy and Nova walk toward the glowing Portal.",
        mode=StoryMode.PLAYGROUND,
        asset_ids=[character.asset_id, world.asset_id],
        hook="Nancy and Nova arrive in the village.",
    )
    episode = EpisodeService(repo).create_from_story(story.story_id)
    episode = SceneBreakdownService(repo).build_from_story(
        episode.episode_id
    )
    episode = ShotPlanService(repo).build_for_episode(
        episode.episode_id
    )

    (
        project_root,
        director,
        storyboard,
        renderer,
        assembly,
        package,
        production,
    ) = _runtime_services(repo, tmp_path)

    # Use the real Director fingerprint for each approved Storyboard frame.
    for scene in episode.scenes:
        for shot in scene.shots:
            session = director.build(
                episode_id=episode.episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            frame_path = (
                project_root
                / "godot/runtime_state/storyboards"
                / episode.episode_id
                / f"{shot.shot_id}.png"
            )
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            frame_path.write_bytes(PNG_1X1)
            episode.storyboard_frames[shot.shot_id] = (
                StoryboardFrameRecord(
                    episode_id=episode.episode_id,
                    scene_id=scene.scene_id,
                    shot_id=shot.shot_id,
                    source_fingerprint=session.source_fingerprint,
                    status="ready",
                    frame_path=str(
                        frame_path.relative_to(project_root)
                    ),
                    capture_time_seconds=(
                        shot.duration_seconds * 0.5
                    ),
                    review_status="approved",
                    review_source_fingerprint=(
                        session.source_fingerprint
                    ),
                )
            )
    repo.save_episode(episode)

    # Real render receipts, fake MP4 bytes only at the media boundary.
    for scene in episode.scenes:
        for shot in scene.shots:
            rendered = renderer.render_shot(
                episode_id=episode.episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            assert rendered.status == "rendered"

    assembled = assembly.assemble(episode.episode_id)
    assert assembled.status == "ready"

    published = package.generate(episode.episode_id)
    assert published.status == "ready"
    assert published.story_id == story.story_id
    assert published.world_asset_id == world.asset_id
    assert published.asset_ids == [
        character.asset_id,
        world.asset_id,
    ]

    complete = production.status(episode.episode_id)
    assert complete.progress_percent == 100
    assert complete.next_action == "complete"
    assert complete.assembly_ready is True
    assert complete.final_package_ready is True

    package_manifest = json.loads(
        (
            project_root / published.manifest_path
        ).read_text(encoding="utf-8")
    )
    assert package_manifest["story_id"] == story.story_id
    assert package_manifest["world_asset_id"] == world.asset_id
    assert package_manifest["asset_ids"] == [
        character.asset_id,
        world.asset_id,
    ]

    # Durable restart: same production chain is still current.
    restarted = SQLiteStudioRepository(db_path)
    (
        _project_root2,
        _director2,
        _storyboard2,
        _renderer2,
        assembly2,
        package2,
        production2,
    ) = _runtime_services(restarted, tmp_path)

    after_restart = production2.status(episode.episode_id)
    assert after_restart.progress_percent == 100
    assert after_restart.next_action == "complete"
    assert assembly2.status_for(episode.episode_id).status == "ready"
    assert package2.status_for(episode.episode_id).status == "ready"

    # No shadow Character/World/Equipment assets were created.
    assert {
        asset.asset_id
        for asset in restarted.list_assets()
    } == original_asset_ids | {
        asset.asset_id
        for asset in restarted.list_assets(AssetType.EQUIPMENT)
    }

    # Change one source Shot: all downstream truth must stop claiming 100%.
    changed_episode = restarted.get_episode(episode.episode_id)
    changed_episode.scenes[0].shots[0] = (
        changed_episode.scenes[0].shots[0].model_copy(
            update={"action": "Nancy turns and runs toward the Portal."}
        )
    )
    restarted.save_episode(changed_episode)

    stale = production2.status(episode.episode_id)
    assert stale.progress_percent < 100
    assert stale.next_action == "generate_storyboard"
    assert assembly2.status_for(episode.episode_id).status == "stale"
    assert package2.status_for(episode.episode_id).status == "stale"


def test_completion_card_and_publish_stage_are_visible():
    root = Path(__file__).resolve().parents[1]
    ui = (
        root / "studio" / "ui" / "creator" / "episodes.py"
    ).read_text(encoding="utf-8")

    assert "publish_package" in ui
    assert "First Production Loop Complete" in ui
    assert "第一次完整制作闭环完成" in ui
    assert "Story → Episode → Scene → Shot" in ui
