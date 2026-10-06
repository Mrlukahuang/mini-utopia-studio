import json
from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot
from studio.models.equipment_runtime import EquipmentRuntimeSpec
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.equipment_service import EquipmentService


ROOT = Path(__file__).resolve().parents[1]


def _character(repo: SQLiteStudioRepository) -> Asset:
    profile = CharacterProfile()
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Runtime Hero",
        slug="runtime-hero",
        metadata={
            "character_profile": profile.model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def test_runtime_spec_uses_same_owned_collection_and_loadout(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    service = EquipmentService(repo)
    collection = service.ensure_starter_collection()
    definitions = service.list_definitions()

    wanted_slots = {
        EquipmentSlot.WEAPON_MAIN,
        EquipmentSlot.BACKPACK,
        EquipmentSlot.WINGS,
    }
    for item in collection.items:
        definition = definitions[item.definition_id]
        if definition.slot in wanted_slots:
            service.equip(
                character_asset_id=character.asset_id,
                item_instance_id=item.item_instance_id,
            )

    spec = service.runtime_spec(character.asset_id)

    assert spec.character_asset_id == character.asset_id
    assert spec.rig_family == "humanoid_kaykit_v1"
    assert set(spec.equipped) >= {
        "weapon_main",
        "backpack",
        "wings",
    }
    assert (
        spec.equipped["weapon_main"].item_instance_id
        == service.loadout_for(character.asset_id).weapon_main_item_id
    )
    assert spec.final_stats == service.final_stats(character.asset_id)


def test_runtime_spec_json_round_trip(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    service = EquipmentService(repo)

    target = tmp_path / "loadout.json"
    service.export_runtime_spec(
        character_asset_id=character.asset_id,
        target_path=target,
    )

    restored = EquipmentRuntimeSpec.model_validate_json(
        target.read_text(encoding="utf-8")
    )

    assert restored.character_asset_id == character.asset_id
    assert "Socket_Weapon_R" in restored.socket_names
    assert restored.final_stats.hp >= 100


def test_committed_godot_smoke_payload_matches_python_runtime_schema():
    path = (
        ROOT
        / "godot"
        / "config"
        / "runtime"
        / "equipment_smoke_v0_1.json"
    )
    payload = EquipmentRuntimeSpec.model_validate_json(
        path.read_text(encoding="utf-8")
    )

    assert payload.rig_family == "humanoid_kaykit_v1"
    assert payload.final_stats.hp == 129
    assert payload.final_stats.atk == 26
    assert payload.final_stats.defense == 19
    assert set(payload.equipped) == {
        "outfit",
        "weapon_main",
        "backpack",
        "wings",
        "accessory",
    }
    assert payload.equipped["weapon_main"].animation_class == "one_handed"


def test_godot_equipment_runtime_uses_locked_avatar_sockets():
    runtime = (
        ROOT / "godot" / "scripts" / "equipment_runtime.gd"
    ).read_text(encoding="utf-8")
    contract = (
        ROOT / "godot" / "scripts" / "avatar_contract.gd"
    ).read_text(encoding="utf-8")
    smoke = (
        ROOT / "godot" / "scripts" / "equipment_runtime_smoke_test.gd"
    ).read_text(encoding="utf-8")
    scene = (
        ROOT / "godot" / "scenes" / "equipment_runtime_smoke_test.tscn"
    ).read_text(encoding="utf-8")

    assert "SOCKET_WEAPON_R" in runtime
    assert "SOCKET_BACKPACK" in runtime
    assert "SOCKET_WINGS" in runtime
    assert "SOCKET_ACCESSORY" in runtime
    assert "apply_default_socket_positions" in contract
    assert "MiniUtopiaEquipmentRuntime.attach_loadout" in smoke
    assert "Slim / Standard / Chubby" in smoke
    assert "equipment_runtime_smoke_test.gd" in scene


def test_runtime_smoke_payload_is_plain_json_for_godot():
    path = (
        ROOT
        / "godot"
        / "config"
        / "runtime"
        / "equipment_smoke_v0_1.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == "1.0"
    assert data["body_type"] == "standard"
    assert data["equipped"]["weapon_main"]["rarity"] == "purple"
