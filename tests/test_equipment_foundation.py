from pathlib import Path

import pytest

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import (
    RARITY_POWER_MULTIPLIER,
    CreatorCollection,
    EquipmentDefinition,
    EquipmentRarity,
    EquipmentSlot,
    StatBlock,
    create_equipment_instance,
    deterministic_roll,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.equipment_service import EquipmentService


ROOT = Path(__file__).resolve().parents[1]


def _definition() -> EquipmentDefinition:
    return EquipmentDefinition(
        definition_id="EQ_TEST_SWORD",
        display_name="Test Sword",
        slot=EquipmentSlot.WEAPON_MAIN,
        compatible_tags=["humanoid"],
        base_stats=StatBlock(atk=8),
    )


def test_same_seed_produces_same_rolled_stats():
    definition = _definition()

    first = deterministic_roll(
        definition=definition,
        rarity=EquipmentRarity.PURPLE,
        item_level=3,
        generation_seed="same-seed",
    )
    second = deterministic_roll(
        definition=definition,
        rarity=EquipmentRarity.PURPLE,
        item_level=3,
        generation_seed="same-seed",
    )

    assert first == second


def test_rarity_power_budget_is_bounded_and_monotonic():
    definition = _definition()
    powers = []

    for rarity in EquipmentRarity:
        stats = deterministic_roll(
            definition=definition,
            rarity=rarity,
            item_level=1,
            generation_seed="budget-check",
        )
        expected = round(
            definition.base_stats.power
            * RARITY_POWER_MULTIPLIER[rarity]
        )
        assert stats.power == max(definition.base_stats.power, expected)
        powers.append(stats.power)

    assert powers == sorted(powers)


def test_same_definition_can_create_distinct_owned_instances():
    definition = _definition()
    first = create_equipment_instance(
        definition=definition,
        rarity=EquipmentRarity.BLUE,
        generation_seed="duplicate-definition",
    )
    second = create_equipment_instance(
        definition=definition,
        rarity=EquipmentRarity.BLUE,
        generation_seed="duplicate-definition",
    )

    assert first.item_instance_id != second.item_instance_id
    assert first.definition_id == second.definition_id
    assert first.rolled_stats == second.rolled_stats


def _character(repo: SQLiteStudioRepository, name: str = "Nova") -> Asset:
    profile = CharacterProfile()
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name=name,
        slug=name.lower(),
        metadata={
            "character_profile": profile.model_dump(mode="json"),
        },
    )
    repo.save_asset(asset)
    return asset


def test_starter_collection_persists_and_equipping_updates_final_stats(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    character = _character(repo)
    service = EquipmentService(repo)

    collection = service.ensure_starter_collection()
    definitions = service.list_definitions()

    assert {
        item.rarity
        for item in collection.items
    } >= {
        EquipmentRarity.GREEN,
        EquipmentRarity.BLUE,
        EquipmentRarity.PURPLE,
    }

    sword = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot == EquipmentSlot.WEAPON_MAIN
    )

    base = service.base_stats(character.asset_id)
    service.equip(
        character_asset_id=character.asset_id,
        item_instance_id=sword.item_instance_id,
    )
    final = service.final_stats(character.asset_id)

    assert final.atk == base.atk + sword.rolled_stats.atk
    assert final.hp == base.hp + sword.rolled_stats.hp
    assert final.defense == base.defense + sword.rolled_stats.defense

    reloaded_repo = SQLiteStudioRepository(db_path)
    reloaded = EquipmentService(reloaded_repo)
    loadout = reloaded.loadout_for(character.asset_id)

    assert loadout.weapon_main_item_id == sword.item_instance_id
    assert reloaded.final_stats(character.asset_id) == final


def test_unequip_restores_base_stats(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    service = EquipmentService(repo)
    collection = service.ensure_starter_collection()
    definitions = service.list_definitions()

    item = next(
        item
        for item in collection.items
        if definitions[item.definition_id].slot == EquipmentSlot.BACKPACK
    )

    service.equip(
        character_asset_id=character.asset_id,
        item_instance_id=item.item_instance_id,
    )
    assert service.final_stats(character.asset_id) != service.base_stats(
        character.asset_id
    )

    service.unequip(
        character_asset_id=character.asset_id,
        slot=EquipmentSlot.BACKPACK,
    )

    assert service.final_stats(character.asset_id) == service.base_stats(
        character.asset_id
    )


def test_incompatible_equipment_is_rejected(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = _character(repo)
    service = EquipmentService(repo)

    incompatible_asset = Asset.create(
        AssetType.EQUIPMENT,
        display_name="Robot Core",
        slug="robot-core-test",
    )
    incompatible_definition = EquipmentDefinition(
        definition_id=incompatible_asset.asset_id,
        display_name="Robot Core",
        slot=EquipmentSlot.ACCESSORY,
        compatible_tags=["robot-only"],
        base_stats=StatBlock(defense=5),
    )
    incompatible_asset.metadata["equipment_definition"] = (
        incompatible_definition.model_dump(mode="json")
    )
    repo.save_asset(incompatible_asset)

    item = create_equipment_instance(
        definition=incompatible_definition,
        rarity=EquipmentRarity.GREEN,
        generation_seed="robot-only",
    )
    service.add_instance(item)

    with pytest.raises(ValueError, match="incompatible"):
        service.equip(
            character_asset_id=character.asset_id,
            item_instance_id=item.item_instance_id,
        )


def test_creator_collection_rejects_duplicate_item_ids():
    definition = _definition()
    item = create_equipment_instance(
        definition=definition,
        rarity=EquipmentRarity.GREEN,
        generation_seed="one",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        CreatorCollection(items=[item, item])


def test_my_stuff_is_wired_into_creator_navigation():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    page = (
        ROOT / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")

    assert '"🎒 My Stuff"' in app
    assert "render_my_stuff(ctx)" in app
    assert "Choose Character / 选择角色" in page
    assert "Equip / 装备" in page
    assert "HP" in page
    assert "ATK" in page
    assert "DEF" in page
