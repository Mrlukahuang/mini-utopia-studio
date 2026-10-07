from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.world import WorldBlueprint, WorldProfile
from studio.models.world_creative import CreativePropType
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.runtime.three_world import build_world_runtime_html
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.play_session_service import CreatorPlaySessionService
from studio.services.world_creative_layout_service import WorldCreativeLayoutService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def _world(repo: SQLiteStudioRepository) -> Asset:
    blueprint = WorldBlueprint(location_asset_id="LOC_CREATIVE")
    asset = Asset.create(
        AssetType.LOCATION,
        display_name="Creative Village",
        slug="creative-village",
        metadata={
            "world_profile": WorldProfile(
                world_name="Creative Village"
            ).model_dump(mode="json"),
            "world_blueprint": blueprint.model_dump(mode="json"),
            "canon_marker": "BASE_WORLD_UNCHANGED",
        },
    )
    repo.save_asset(asset)
    return asset


def _character(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Nancy",
        slug="nancy",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def test_creative_layout_is_additive_persistent_and_safe_to_clear(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    world = _world(repo)
    base_blueprint = repo.get_asset(world.asset_id).metadata["world_blueprint"]

    service = WorldCreativeLayoutService(repo)
    lamp = service.place(
        world_asset_id=world.asset_id,
        prop_type=CreativePropType.STAR_LAMP,
        position=(25.0, 0.0, 27.0),
        rotation_y=45.0,
        scale=1.2,
    )
    service.place(
        world_asset_id=world.asset_id,
        prop_type=CreativePropType.TOY_BENCH,
        position=(18.0, 0.0, 24.0),
    )

    restarted = SQLiteStudioRepository(db_path)
    layout = WorldCreativeLayoutService(restarted).get_layout(world.asset_id)
    assert len(layout.decorations) == 2
    assert layout.decorations[0].decoration_id == lamp.decoration_id

    persisted_world = restarted.get_asset(world.asset_id)
    assert persisted_world.metadata["world_blueprint"] == base_blueprint
    assert persisted_world.metadata["canon_marker"] == "BASE_WORLD_UNCHANGED"

    WorldCreativeLayoutService(restarted).clear(world.asset_id)
    cleared_world = restarted.get_asset(world.asset_id)
    assert (
        WorldCreativeLayoutService(restarted)
        .get_layout(world.asset_id)
        .decorations
        == []
    )
    assert cleared_world.metadata["world_blueprint"] == base_blueprint
    assert cleared_world.metadata["canon_marker"] == "BASE_WORLD_UNCHANGED"


def test_creative_layout_flows_to_play_session_and_browser_runtime(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    world = _world(repo)
    character = _character(repo)

    creative = WorldCreativeLayoutService(repo)
    creative.place(
        world_asset_id=world.asset_id,
        prop_type=CreativePropType.MINI_FLAG,
        position=(30.0, 0.0, 32.0),
        rotation_y=90.0,
    )

    session = CreatorPlaySessionService(
        repo,
        CharacterRuntimeService(
            repo,
            LocalObjectStorage(tmp_path / "storage"),
        ),
        export_path=tmp_path / "play_session.json",
    ).export(
        character_asset_id=character.asset_id,
        world_asset_id=world.asset_id,
    )

    assert session.creative_layout is not None
    assert len(session.creative_layout.decorations) == 1
    assert session.creative_layout.decorations[0].prop_type == CreativePropType.MINI_FLAG

    html = build_world_runtime_html(
        world_name=world.display_name,
        profile=WorldProfile.model_validate(
            world.metadata["world_profile"]
        ),
        blueprint=WorldBlueprint.model_validate(
            world.metadata["world_blueprint"]
        ),
        creative_layout=session.creative_layout,
    )
    assert "creativeLayout" in html
    assert "addCreativeDecoration" in html
    assert "mini_flag" in html
    assert "Creative_" in html


def test_creative_play_is_visible_and_godot_consumes_same_delta():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ui = (
        ROOT / "studio" / "ui" / "creator" / "creative_play.py"
    ).read_text(encoding="utf-8")
    creator = (
        ROOT / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")
    runtime = (
        ROOT / "godot" / "scripts" / "world_creative_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "render_creative_play(" in app
    assert "Creative Play / 装饰我的世界" in ui
    assert "Place Decoration / 放进去" in ui
    assert 'payload.get("creative_layout", {})' in creator
    assert "MiniUtopiaWorldCreativeRuntime" in creator
    assert "WORLD-02 Creative layout" in runtime
    assert '"star_lamp"' in runtime
    assert '"flower_pot"' in runtime
    assert '"toy_bench"' in runtime
    assert '"mini_flag"' in runtime
    assert '"cloud_cushion"' in runtime
