from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import CreatorCollection
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.equipment_service import EquipmentService


ROOT = Path(__file__).resolve().parents[1]


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


def test_old_collection_payload_without_favorites_remains_compatible():
    collection = CreatorCollection.model_validate(
        {
            "collection_id": "COLL_OLD",
            "owner_key": "default_creator",
            "items": [],
            "loadouts": {},
            "claimed_drop_ids": [],
            "claimed_quest_reward_ids": [],
        }
    )
    assert collection.favorite_item_ids == []


def test_favorite_toggle_persists_through_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    _character(repo)
    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    item = max(collection.items, key=lambda value: value.created_at)

    equipment.set_favorite(
        item_instance_id=item.item_instance_id,
        favorite=True,
    )

    restarted = EquipmentService(SQLiteStudioRepository(db_path))
    saved = restarted.ensure_starter_collection()
    assert item.item_instance_id in saved.favorite_item_ids

    restarted.set_favorite(
        item_instance_id=item.item_instance_id,
        favorite=False,
    )
    reloaded = EquipmentService(SQLiteStudioRepository(db_path))
    assert item.item_instance_id not in (
        reloaded.ensure_starter_collection().favorite_item_ids
    )


def test_collection_progress_ui_has_newest_completion_favorites_and_compare():
    page = (
        ROOT / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")

    assert "Newest / 最近获得" in page
    assert "⭐ Favorites" in page
    assert "🧩 Slots" in page
    assert "favorite_item_ids" in page
    assert "ctx.equipment.set_favorite(" in page
    assert "Compared with current" in page
    assert "_stat_delta(" in page
