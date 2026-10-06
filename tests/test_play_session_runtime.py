from pathlib import Path

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.baby import BabyRuntimeSpec
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot
from studio.models.play_session import PlaySessionRuntimeSpec
from studio.models.world import WorldProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.equipment_service import EquipmentService
from studio.services.play_session_service import CreatorPlaySessionService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def _character(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Play Hero",
        slug="play-hero",
        status=ReviewStatus.APPROVED,
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def _world(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.LOCATION,
        display_name="Newbie Village",
        slug="newbie-village",
        status=ReviewStatus.APPROVED,
        metadata={"world_profile": WorldProfile().model_dump(mode="json")},
    )
    repo.save_asset(asset)
    return asset


def test_play_session_round_trip_contains_character_equipment_baby_and_world(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    character = _character(repo)
    world = _world(repo)

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    for wanted in (
        EquipmentSlot.WEAPON_MAIN,
        EquipmentSlot.WEAPON_OFFHAND,
        EquipmentSlot.HEADWEAR,
    ):
        item = next(
            item
            for item in collection.items
            if definitions[item.definition_id].slot == wanted
        )
        equipment.equip(
            character_asset_id=character.asset_id,
            item_instance_id=item.item_instance_id,
        )

    babies = BabyService(repo)
    babies.create_initial_baby(display_name="Nova", species_id="star_baby")

    target = tmp_path / "creator_play_session.json"
    service = CreatorPlaySessionService(
        repo,
        CharacterRuntimeService(repo, storage),
        equipment=equipment,
        babies=babies,
        export_path=target,
    )
    exported = service.export(
        character_asset_id=character.asset_id,
        world_asset_id=world.asset_id,
    )
    restored = PlaySessionRuntimeSpec.model_validate_json(
        target.read_text(encoding="utf-8")
    )

    assert restored.character_asset_id == character.asset_id
    assert restored.character_name == "Play Hero"
    assert restored.world_asset_id == world.asset_id
    assert restored.world_name == "Newbie Village"
    assert restored.character.rig_family == "humanoid_kaykit_v1"
    assert set(restored.equipment.equipped) >= {
        "weapon_main",
        "weapon_offhand",
        "headwear",
    }
    assert restored.baby is not None
    assert restored.baby.display_name == "Nova"
    assert restored == exported


def test_committed_play_session_example_matches_runtime_schema():
    path = (
        ROOT
        / "godot"
        / "config"
        / "runtime"
        / "creator_play_session_example.json"
    )
    payload = PlaySessionRuntimeSpec.model_validate_json(
        path.read_text(encoding="utf-8")
    )

    assert payload.schema_version == "1.0"
    assert payload.character_asset_id == payload.equipment.character_asset_id
    assert payload.equipment.equipped["weapon_main"].slot == EquipmentSlot.WEAPON_MAIN
    assert payload.equipment.equipped["weapon_offhand"].slot == EquipmentSlot.WEAPON_OFFHAND
    assert payload.equipment.equipped["headwear"].slot == EquipmentSlot.HEADWEAR
    assert isinstance(payload.baby, BabyRuntimeSpec)
    assert payload.baby.follow_enabled is True


def test_dressing_room_and_explore_world_export_same_play_session():
    room = (
        ROOT / "studio" / "ui" / "creator" / "dressing_room.py"
    ).read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "Play This Loadout / 带这套装备出发" in room
    assert "CreatorPlaySessionService" in room
    assert "pending_app_page = \"🎮 Explore World\"" in room
    assert "play_session_service = CreatorPlaySessionService" in app
    assert "play_session_service.export(" in app
    assert "Godot Play Session Ready" in app


def test_local_runtime_state_is_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "godot/runtime_state/*.json" in gitignore
