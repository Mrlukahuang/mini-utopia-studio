from __future__ import annotations

from pathlib import Path

from studio.bridge.equipment import EquipmentBridgeGateway
from studio.bridge.server import BridgeApplication, build_server
from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.repositories.sqlite import SQLiteStudioRepository


DB_PATH = Path("/tmp/mini-utopia-equipment-bridge-smoke.db")
CHARACTER_ID = "CHAR_EQUIPMENT_SMOKE"


def build_application() -> BridgeApplication:
    if DB_PATH.exists():
        DB_PATH.unlink()

    repo = SQLiteStudioRepository(DB_PATH)
    character = Asset(
        asset_id=CHARACTER_ID,
        asset_type=AssetType.CHARACTER,
        display_name="Equipment Smoke Hero",
        slug="equipment-smoke-hero",
        status=ReviewStatus.APPROVED,
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(character)

    gateway = EquipmentBridgeGateway(repo)
    return BridgeApplication(
        equipment_gateway_factory=lambda: gateway,
    )


if __name__ == "__main__":
    server = build_server(
        host="127.0.0.1",
        port=8766,
        application=build_application(),
    )
    print("bridge_godot_equipment_smoke_server: READY", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if DB_PATH.exists():
            DB_PATH.unlink()
