from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentRarity, create_equipment_instance
from studio.models.quest import QuestObjective, QuestObjectiveType
from studio.models.world_creative import CreativePropType
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.adventure_hub_service import AdventureHubService
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.quest_service import QuestService
from studio.services.world_creative_layout_service import WorldCreativeLayoutService
from studio.services.world_gameplay_layer_service import WorldGameplayLayerService


ROOT = Path(__file__).resolve().parents[1]


def _world(repo: SQLiteStudioRepository) -> Asset:
    asset = Asset.create(
        AssetType.LOCATION,
        display_name="Hub Village",
        slug="hub-village",
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


def test_adventure_hub_empty_state_is_safe(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    hub = AdventureHubService(repo).status()

    assert hub.quest is None
    assert hub.baby is None
    assert hub.world is None
    assert hub.continue_page == "🌍 World Factory"


def test_adventure_hub_rebuilds_from_durable_progress_after_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    world = _world(repo)
    _character(repo)

    BabyService(repo).create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    baby = BabyService(repo).active_baby()
    assert baby is not None
    BabyService(repo).add_xp(baby_id=baby.baby_id, amount=50)
    BabyService(repo).add_bond(baby_id=baby.baby_id, amount=20)

    quest = QuestService(repo).create_quest(
        title="Portal Picnic Adventure",
        world_asset_id=world.asset_id,
        objectives=[
            QuestObjective(
                objective_id="visit_portal",
                objective_type=QuestObjectiveType.GO_TO_LOCATION,
                label="Visit the Portal",
                target_id="portal",
                order=0,
            )
        ],
    )
    WorldGameplayLayerService(repo).register_quest(quest.quest_id)

    WorldCreativeLayoutService(repo).place(
        world_asset_id=world.asset_id,
        prop_type=CreativePropType.STAR_LAMP,
        position=(25.0, 0.0, 27.0),
    )

    equipment = EquipmentService(repo)
    collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    definition = next(iter(definitions.values()))
    newest = create_equipment_instance(
        definition=definition,
        rarity=EquipmentRarity.GOLD,
        generation_seed="HUB_LATEST_REWARD",
    )
    collection.items.append(newest)
    repo.save_collection(collection)

    restarted = SQLiteStudioRepository(db_path)
    hub = AdventureHubService(restarted).status()

    assert hub.quest is not None
    assert hub.quest.quest_id == quest.quest_id
    assert hub.quest.world_name == "Hub Village"
    assert hub.continue_page == "🪞 Dressing Room"

    assert hub.baby is not None
    assert hub.baby.display_name == "Nova"
    assert hub.baby.xp == 50
    assert hub.baby.bond == 20

    assert hub.latest_reward is not None
    assert hub.latest_reward.item_instance_id == newest.item_instance_id
    assert hub.latest_reward.rarity == EquipmentRarity.GOLD

    assert hub.world is not None
    assert hub.world.world_asset_id == world.asset_id
    assert "quest" in hub.world.modes
    assert "creative" in hub.world.modes
    assert hub.world.quest_count == 1
    assert hub.world.decoration_count == 1


def test_home_renders_adventure_hub_and_keeps_first_loop_milestone():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ui = (
        ROOT / "studio" / "ui" / "creator" / "adventure_hub.py"
    ).read_text(encoding="utf-8")

    assert "render_adventure_hub(ctx)" in app
    assert "First Adventure Milestone / 第一次冒险里程碑" in app
    assert "Adventure Hub / 冒险大厅" in ui
    assert "Continue Adventure / 继续冒险" in ui
    assert "Active Baby / 当前宝宝" in ui
    assert "Latest Reward / 最新收获" in ui
    assert "World Progress / 世界进度" in ui
    assert 'active_quest_id = hub.quest.quest_id' in ui
