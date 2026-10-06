from pathlib import Path

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.runtime.avatar_preview_3d import build_avatar_preview_html
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService


ROOT = Path(__file__).resolve().parents[1]


def _character(repo: SQLiteStudioRepository) -> Asset:
    profile = CharacterProfile()
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Dressing Hero",
        slug="dressing-hero",
        status=ReviewStatus.APPROVED,
        metadata={"character_profile": profile.model_dump(mode="json")},
    )
    repo.save_asset(asset)
    return asset


def test_dressing_room_combines_persisted_equipment_and_baby(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    character = _character(repo)

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()

    sword = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot == EquipmentSlot.WEAPON_MAIN
    )
    equipment.equip(
        character_asset_id=character.asset_id,
        item_instance_id=sword.item_instance_id,
    )

    babies = BabyService(repo)
    roster = babies.create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    baby_id = roster.active_baby_id

    # New repository/services emulate a full Streamlit process restart.
    reloaded_repo = SQLiteStudioRepository(db_path)
    reloaded_equipment = EquipmentService(reloaded_repo)
    reloaded_babies = BabyService(reloaded_repo)

    equipment_spec = reloaded_equipment.runtime_spec(character.asset_id)
    baby_spec = reloaded_babies.runtime_spec()

    assert equipment_spec.equipped["weapon_main"].item_instance_id == sword.item_instance_id
    assert equipment_spec.final_stats.atk > reloaded_equipment.base_stats(character.asset_id).atk
    assert baby_spec is not None
    assert baby_spec.baby_id == baby_id
    assert baby_spec.display_name == "Nova"


def test_shared_webgl_stage_accepts_equipment_and_baby_payloads(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    profile = CharacterProfile.model_validate(
        character.metadata["character_profile"]
    )

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    sword = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot == EquipmentSlot.WEAPON_MAIN
    )
    equipment.equip(
        character_asset_id=character.asset_id,
        item_instance_id=sword.item_instance_id,
    )

    babies = BabyService(repo)
    babies.create_initial_baby(display_name="Nova", species_id="star_baby")

    html = build_avatar_preview_html(
        profile.avatar,
        equipment=equipment.runtime_spec(character.asset_id),
        baby=babies.runtime_spec(),
    )

    assert "Equipment_Weapon_Main" in html
    assert sword.item_instance_id in html
    assert "ActiveBaby_" in html
    assert "Nova" in html
    assert "star_baby" in html
    assert "Socket_Weapon_R" in html


def test_dressing_room_is_child_visible_and_uses_shared_runtime():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    room = (
        ROOT / "studio" / "ui" / "creator" / "dressing_room.py"
    ).read_text(encoding="utf-8")
    preview = (
        ROOT / "studio" / "ui" / "creator" / "avatar_preview.py"
    ).read_text(encoding="utf-8")

    assert "🪞 Dressing Room" in app
    assert "render_dressing_room(ctx)" in app
    assert "render_avatar_preview(" in room
    assert "equipment=equipment_spec" in room
    assert "baby=baby_spec" in room
    assert "Quick Equip / 快速换装" in room
    assert "CharacterLoadout" in room
    assert "equipment: EquipmentRuntimeSpec | None = None" in preview
    assert "baby: BabyRuntimeSpec | None = None" in preview


def test_dressing_room_supports_all_five_canonical_slots():
    room = (
        ROOT / "studio" / "ui" / "creator" / "dressing_room.py"
    ).read_text(encoding="utf-8")
    runtime = (
        ROOT / "studio" / "runtime" / "avatar_preview_3d.py"
    ).read_text(encoding="utf-8")

    for slot in EquipmentSlot:
        assert slot.value in runtime or "for slot in EquipmentSlot" in room

    assert "Equipment_Backpack" in runtime
    assert "Equipment_Wings" in runtime
    assert "Equipment_Accessory" in runtime
