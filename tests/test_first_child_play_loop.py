import json
from pathlib import Path

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.combat_drop_service import CombatDropService
from studio.services.equipment_service import EquipmentService
from studio.services.first_adventure_progress_service import (
    FirstAdventureProgressService,
)
from studio.services.play_session_service import CreatorPlaySessionService
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def _character(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Loop Hero",
        slug="loop-hero",
        status=ReviewStatus.APPROVED,
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def _equip_slot(
    equipment: EquipmentService,
    *,
    character_asset_id: str,
    slot: EquipmentSlot,
):
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    item = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot == slot
    )
    equipment.equip(
        character_asset_id=character_asset_id,
        item_instance_id=item.item_instance_id,
    )
    return item


def test_first_adventure_progress_is_derived_from_durable_state(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    progress = FirstAdventureProgressService(repo)

    empty = progress.status()
    assert empty.completed_steps == 0
    assert empty.loop_complete is False

    character = _character(repo)
    after_character = progress.status()
    assert after_character.has_character is True
    assert after_character.character_asset_id == character.asset_id
    assert after_character.has_active_baby is False
    assert after_character.gear_ready is False
    assert after_character.reward_claimed is False

    BabyService(repo).create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    _equip_slot(
        EquipmentService(repo),
        character_asset_id=character.asset_id,
        slot=EquipmentSlot.WEAPON_MAIN,
    )

    ready = progress.status()
    assert ready.completed_steps == 3
    assert ready.has_active_baby is True
    assert ready.gear_ready is True
    assert ready.reward_claimed is False
    assert ready.loop_complete is False


def test_first_child_play_loop_survives_restart_and_reenters_stronger(tmp_path):
    db_path = tmp_path / "studio.db"
    inbox_path = tmp_path / "combat_drop_inbox.json"
    session_one_path = tmp_path / "play_session_one.json"
    session_two_path = tmp_path / "play_session_two.json"
    storage_path = tmp_path / "storage"

    repo = SQLiteStudioRepository(db_path)
    character = _character(repo)
    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )

    equipment = EquipmentService(repo)
    _equip_slot(
        equipment,
        character_asset_id=character.asset_id,
        slot=EquipmentSlot.WEAPON_MAIN,
    )
    starter_shield = _equip_slot(
        equipment,
        character_asset_id=character.asset_id,
        slot=EquipmentSlot.WEAPON_OFFHAND,
    )

    runtime = CharacterRuntimeService(
        repo,
        LocalObjectStorage(storage_path),
    )
    session_one = CreatorPlaySessionService(
        repo,
        runtime,
        equipment=equipment,
        babies=babies,
        export_path=session_one_path,
    ).export(character_asset_id=character.asset_id)

    assert session_one.baby is not None
    assert session_one.baby.display_name == "Nova"
    assert (
        session_one.equipment.equipped["weapon_offhand"].item_instance_id
        == starter_shield.item_instance_id
    )
    first_power = session_one.equipment.final_stats.power

    inbox_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "drops": [
                    {
                        "drop_id": "DROP_LOOP_TRAINING_SKELETON_01",
                        "source_enemy": "training_skeleton_01",
                        "definition_slug": "reward_bone_buckler",
                        "rarity": "blue",
                        "item_level": 1,
                        "generation_seed": "DROP_LOOP_BONE_BUCKLER",
                        "character_asset_id": character.asset_id,
                        "created_at": "1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    claims = CombatDropService(
        repo,
        inbox_path=inbox_path,
        equipment=equipment,
    ).claim_available()
    assert len(claims) == 1
    assert claims[0].display_name == "Bone Buckler / 骨盾"

    claimed_status = FirstAdventureProgressService(
        repo,
        equipment=equipment,
        babies=babies,
    ).status()
    assert claimed_status.reward_claimed is True
    assert claimed_status.loop_complete is True
    assert claimed_status.reward_equipped is False

    equipment.equip(
        character_asset_id=character.asset_id,
        item_instance_id=claims[0].item_instance_id,
    )
    equipped_status = FirstAdventureProgressService(
        repo,
        equipment=equipment,
        babies=babies,
    ).status()
    assert equipped_status.reward_equipped is True

    # Full process restart: rebuild repository, services, storage and session.
    reloaded_repo = SQLiteStudioRepository(db_path)
    reloaded_equipment = EquipmentService(reloaded_repo)
    reloaded_babies = BabyService(reloaded_repo)
    reloaded_runtime = CharacterRuntimeService(
        reloaded_repo,
        LocalObjectStorage(storage_path),
    )

    after_restart = FirstAdventureProgressService(
        reloaded_repo,
        equipment=reloaded_equipment,
        babies=reloaded_babies,
    ).status()
    assert after_restart.loop_complete is True
    assert after_restart.reward_equipped is True
    assert "weapon_offhand" in after_restart.equipped_slots

    session_two = CreatorPlaySessionService(
        reloaded_repo,
        reloaded_runtime,
        equipment=reloaded_equipment,
        babies=reloaded_babies,
        export_path=session_two_path,
    ).export(character_asset_id=character.asset_id)

    assert session_two.baby is not None
    assert session_two.baby.baby_id == session_one.baby.baby_id
    assert (
        session_two.equipment.equipped["weapon_offhand"].display_name
        == "Bone Buckler / 骨盾"
    )
    assert session_two.equipment.final_stats.power > first_power
    assert session_two.equipment.final_stats.defense > session_one.equipment.final_stats.defense

    # The same receipt can never duplicate after restart.
    assert CombatDropService(
        reloaded_repo,
        inbox_path=inbox_path,
        equipment=reloaded_equipment,
    ).claim_available() == []


def test_home_exposes_first_adventure_and_continue_routes_to_dressing_room():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    card = (
        ROOT / "studio" / "ui" / "creator" / "adventure_progress.py"
    ).read_text(encoding="utf-8")

    assert "render_first_adventure_progress(ctx)" in app
    assert '"🪞 Dressing Room",' in app
    assert "First Adventure / 第一次完整冒险" in card
    assert "Continue Adventure / 继续冒险" in card
    assert 'pending_app_page = "🪞 Dressing Room"' in card
    assert "Bone Buckler" in card
    assert "loop_complete" in card
