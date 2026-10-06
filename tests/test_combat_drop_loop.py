import json
from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.combat_drop_service import CombatDropService
from studio.services.equipment_service import EquipmentService


ROOT = Path(__file__).resolve().parents[1]


def _character(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Battle Hero",
        slug="battle-hero",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def _bone_buckler_asset(repo: SQLiteStudioRepository):
    return next(
        asset
        for asset in repo.list_assets(AssetType.EQUIPMENT)
        if asset.slug == "reward_bone_buckler"
    )


def test_bone_buckler_definition_exists_but_is_not_starter_owned(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    reward_asset = _bone_buckler_asset(repo)

    reward_definition = equipment.get_definition(reward_asset.asset_id)
    assert reward_definition.display_name == "Bone Buckler / 骨盾"
    assert reward_definition.slot == EquipmentSlot.WEAPON_OFFHAND

    assert all(
        item.definition_id != reward_definition.definition_id
        for item in collection.items
    )


def test_combat_drop_claim_is_idempotent_and_persists_through_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    inbox_path = tmp_path / "combat_drop_inbox.json"
    repo = SQLiteStudioRepository(db_path)
    character = _character(repo)
    equipment = EquipmentService(repo)
    equipment.ensure_starter_collection()

    inbox_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "drops": [
                    {
                        "drop_id": "DROP_TEST_BONE_001",
                        "source_enemy": "training_skeleton_01",
                        "definition_slug": "reward_bone_buckler",
                        "rarity": "blue",
                        "item_level": 1,
                        "generation_seed": "DROP_TEST_BONE_001_BONE_BUCKLER",
                        "character_asset_id": character.asset_id,
                        "created_at": "1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    drops = CombatDropService(
        repo,
        inbox_path=inbox_path,
        equipment=equipment,
    )
    first = drops.claim_available()
    second = drops.claim_available()

    assert len(first) == 1
    assert first[0].display_name == "Bone Buckler / 骨盾"
    assert first[0].slot == EquipmentSlot.WEAPON_OFFHAND
    assert second == []

    collection = equipment.get_collection()
    assert "DROP_TEST_BONE_001" in collection.claimed_drop_ids
    claimed_item = collection.item_by_id(first[0].item_instance_id)
    assert claimed_item is not None

    equipment.equip(
        character_asset_id=character.asset_id,
        item_instance_id=claimed_item.item_instance_id,
    )
    before_restart = equipment.final_stats(character.asset_id)

    reloaded_repo = SQLiteStudioRepository(db_path)
    reloaded_equipment = EquipmentService(reloaded_repo)
    reloaded_collection = reloaded_equipment.get_collection()
    reloaded_loadout = reloaded_collection.loadout_for(character.asset_id)

    assert "DROP_TEST_BONE_001" in reloaded_collection.claimed_drop_ids
    assert reloaded_loadout.weapon_offhand_item_id == claimed_item.item_instance_id
    assert reloaded_equipment.final_stats(character.asset_id) == before_restart

    # Re-reading the same Godot inbox after a process restart cannot duplicate.
    assert CombatDropService(
        reloaded_repo,
        inbox_path=inbox_path,
        equipment=reloaded_equipment,
    ).claim_available() == []


def test_my_stuff_claims_runtime_rewards_into_collection():
    page = (
        ROOT / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")

    assert "CombatDropService" in page
    assert ".claim_available()" in page
    assert "Battle Reward / 战斗奖励" in page


def test_godot_training_skeleton_uses_creator_stats_and_writes_drop_receipt():
    project = (
        ROOT / "godot" / "project.godot"
    ).read_text(encoding="utf-8")
    player = (
        ROOT / "godot" / "scripts" / "player.gd"
    ).read_text(encoding="utf-8")
    enemy = (
        ROOT / "godot" / "scripts" / "skeleton_enemy.gd"
    ).read_text(encoding="utf-8")
    writer = (
        ROOT / "godot" / "scripts" / "runtime_drop_writer.gd"
    ).read_text(encoding="utf-8")
    village = (
        ROOT
        / "godot"
        / "scripts"
        / "newbie_village_100x100_v0_3.gd"
    ).read_text(encoding="utf-8")
    creator_runtime = (
        ROOT / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "attack={" in project
    assert 'physical_keycode":70' in project
    assert "InputEventMouseButton" in project

    assert "_read_creator_stats()" in player
    assert 'get_meta("mini_utopia_stats"' in player
    assert "_attack_nearest_enemy()" in player
    assert 'get_nodes_in_group("mini_utopia_enemy")' in player
    assert "take_damage(raw_amount: int)" in player
    assert "play_attack_swing()" in player

    assert 'add_to_group("mini_utopia_enemy")' in enemy
    assert "training_skeleton_01" in enemy
    assert '"definition_slug": "reward_bone_buckler"' in enemy
    assert "MiniUtopiaRuntimeDropWriter.write_drop" in enemy

    assert 'INBOX_PATH := "res://runtime_state/combat_drop_inbox.json"' in writer
    assert "drop_id" in writer
    assert "DirAccess.make_dir_recursive_absolute" in writer

    assert "_build_training_skeleton()" in village
    assert "MiniUtopiaSkeletonEnemy.new()" in village
    assert "F / Left Click" in village
    assert '"mini_utopia_session_id"' in creator_runtime
