from __future__ import annotations

import json
from http import HTTPStatus

from studio.bridge.equipment import (
    BRIDGE_EQUIPMENT_SCHEMA_VERSION,
    EquipmentBridgeGateway,
)
from studio.bridge.server import BridgeApplication
from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot, PLAYABLE_EQUIPMENT_SLOTS
from studio.repositories.sqlite import SQLiteStudioRepository


def _character(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Bridge Equipment Hero",
        slug="bridge-equipment-hero",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def test_equipment_bridge_exposes_nine_slots_and_python_final_stats(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    gateway = EquipmentBridgeGateway(repo)

    state = gateway.get_state(character.asset_id)
    assert state is not None
    assert state["schema_version"] == BRIDGE_EQUIPMENT_SCHEMA_VERSION
    assert state["character_id"] == character.asset_id
    assert state["slots"] == [slot.value for slot in PLAYABLE_EQUIPMENT_SLOTS]
    assert state["final_stats"] == state["runtime"]["final_stats"]
    assert {item["slot"] for item in state["items"]} >= {
        slot.value for slot in PLAYABLE_EQUIPMENT_SLOTS
    }


def test_equipment_bridge_equip_unequip_survives_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    character = _character(repo)
    gateway = EquipmentBridgeGateway(repo)

    before = gateway.get_state(character.asset_id)
    assert before is not None
    sword = next(
        item
        for item in before["items"]
        if item["slot"] == EquipmentSlot.WEAPON_MAIN.value
    )

    equipped = gateway.set_slot(
        character.asset_id,
        EquipmentSlot.WEAPON_MAIN.value,
        sword["item_instance_id"],
    )
    assert equipped is not None
    assert (
        equipped["loadout"]["weapon_main_item_id"]
        == sword["item_instance_id"]
    )
    assert equipped["runtime"]["equipped"]["weapon_main"][
        "item_instance_id"
    ] == sword["item_instance_id"]
    assert equipped["final_stats"]["atk"] > before["final_stats"]["atk"]

    restarted = EquipmentBridgeGateway(SQLiteStudioRepository(db_path))
    persisted = restarted.get_state(character.asset_id)
    assert persisted is not None
    assert (
        persisted["loadout"]["weapon_main_item_id"]
        == sword["item_instance_id"]
    )

    unequipped = restarted.set_slot(
        character.asset_id,
        EquipmentSlot.WEAPON_MAIN.value,
        None,
    )
    assert unequipped is not None
    assert unequipped["loadout"]["weapon_main_item_id"] is None
    assert "weapon_main" not in unequipped["runtime"]["equipped"]


def test_equipment_bridge_routes_reject_wrong_slot_and_preserve_ids(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    gateway = EquipmentBridgeGateway(repo)
    app = BridgeApplication(equipment_gateway_factory=lambda: gateway)

    state = app.handle(
        method="GET",
        path=f"/characters/{character.asset_id}/equipment",
    )
    assert state.status == HTTPStatus.OK
    assert state.payload["character_id"] == character.asset_id

    sword = next(
        item
        for item in state.payload["items"]
        if item["slot"] == "weapon_main"
    )

    bad = app.handle(
        method="PUT",
        path=f"/characters/{character.asset_id}/equipment/backpack",
        body=json.dumps(
            {"item_instance_id": sword["item_instance_id"]}
        ).encode("utf-8"),
    )
    assert bad.status == HTTPStatus.BAD_REQUEST
    assert bad.payload["error"] == "invalid_equipment_update"

    equipped = app.handle(
        method="PUT",
        path=f"/characters/{character.asset_id}/equipment/weapon_main",
        body=json.dumps(
            {"item_instance_id": sword["item_instance_id"]}
        ).encode("utf-8"),
    )
    assert equipped.status == HTTPStatus.OK
    assert equipped.payload["character_id"] == character.asset_id
    assert (
        equipped.payload["loadout"]["weapon_main_item_id"]
        == sword["item_instance_id"]
    )

    legacy = app.handle(
        method="PUT",
        path=f"/characters/{character.asset_id}/equipment/outfit",
        body=b'{"item_instance_id":null}',
    )
    assert legacy.status == HTTPStatus.BAD_REQUEST

    missing = app.handle(
        method="GET",
        path="/characters/CHAR_MISSING/equipment",
    )
    assert missing.status == HTTPStatus.NOT_FOUND
