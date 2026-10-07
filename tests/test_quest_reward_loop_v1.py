import json

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.equipment import (
    CreatorCollection,
    EquipmentRarity,
    deterministic_roll,
)
from studio.models.quest import (
    QuestObjective,
    QuestObjectiveType,
    QuestReward,
    QuestRewardType,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.equipment_service import EquipmentService
from studio.services.quest_reward_service import QuestRewardService
from studio.services.quest_service import QuestService


def _character(repo: SQLiteStudioRepository) -> Asset:
    character = Asset.create(
        AssetType.CHARACTER,
        display_name="Reward Hero",
        slug="reward-hero",
        metadata={
            "character_profile": CharacterProfile().model_dump(mode="json"),
        },
    )
    repo.save_asset(character)
    return character


def _world(repo: SQLiteStudioRepository) -> Asset:
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Reward World",
        slug="reward-world",
    )
    repo.save_asset(world)
    return world


def _quest(repo: SQLiteStudioRepository, *, repeatable: bool = False):
    world = _world(repo)
    return QuestService(repo).create_quest(
        title="Portal Reward Quest",
        world_asset_id=world.asset_id,
        objectives=[
            QuestObjective(
                objective_id="open_portal",
                objective_type=QuestObjectiveType.OPEN_PORTAL,
                label="Open Portal",
                target_id="portal_01",
                order=0,
            )
        ],
        rewards=[
            QuestReward(
                reward_id="portal_medal",
                reward_type=QuestRewardType.EQUIPMENT,
                target_id="reward_portal_medal",
                amount=1,
                metadata={"rarity": "purple", "item_level": 2},
            ),
            QuestReward(
                reward_id="future_baby_bond",
                reward_type=QuestRewardType.BABY_BOND,
                amount=5,
            ),
        ],
        repeatable=repeatable,
    )


def _write_completion(path, *, quest_id: str, completion_id: str):
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "completions": [
                    {
                        "completion_id": completion_id,
                        "quest_id": quest_id,
                        "session_id": "PLAY_REWARD_TEST",
                        "character_asset_id": "CHAR_REWARD_TEST",
                        "created_at": "1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_old_collection_payload_remains_compatible():
    old = CreatorCollection.model_validate(
        {
            "collection_id": "COLL_OLD",
            "owner_key": "old",
            "items": [],
            "loadouts": {},
            "claimed_drop_ids": ["DROP_OLD"],
        }
    )
    assert old.claimed_drop_ids == ["DROP_OLD"]
    assert old.claimed_quest_reward_ids == []


def test_nonrepeatable_quest_equipment_reward_is_deterministic_and_idempotent(tmp_path):
    db_path = tmp_path / "studio.db"
    inbox_path = tmp_path / "quest_reward_inbox.json"
    repo = SQLiteStudioRepository(db_path)
    character = _character(repo)
    quest = _quest(repo)

    equipment = EquipmentService(repo)
    before_collection = equipment.ensure_starter_collection()
    definitions = equipment.list_definitions()
    portal_definition = next(
        definition
        for definition in definitions.values()
        if definition.display_name == "Portal Medal / 传送门勋章"
    )
    assert all(
        item.definition_id != portal_definition.definition_id
        for item in before_collection.items
    )

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_PLAY_A",
    )
    rewards = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=equipment,
    ).claim_available()

    assert len(rewards) == 1
    reward = rewards[0]
    assert reward.display_name == "Portal Medal / 传送门勋章"
    assert reward.rarity == EquipmentRarity.PURPLE

    collection = equipment.get_collection()
    item = collection.item_by_id(reward.item_instance_id)
    assert item is not None
    expected_seed = f"QUEST_REWARD::{quest.quest_id}:portal_medal"
    assert item.generation_seed == expected_seed
    assert item.rolled_stats == deterministic_roll(
        definition=portal_definition,
        rarity=EquipmentRarity.PURPLE,
        item_level=2,
        generation_seed=expected_seed,
    )

    # The reward is real equipment: it can be equipped and changes final stats.
    before_stats = equipment.final_stats(character.asset_id)
    equipment.equip(
        character_asset_id=character.asset_id,
        item_instance_id=item.item_instance_id,
    )
    after_stats = equipment.final_stats(character.asset_id)
    assert after_stats.power > before_stats.power

    # A new process/repository cannot claim the same non-repeatable reward.
    restarted_repo = SQLiteStudioRepository(db_path)
    restarted_equipment = EquipmentService(restarted_repo)
    restarted_rewards = QuestRewardService(
        restarted_repo,
        inbox_path=inbox_path,
        equipment=restarted_equipment,
    ).claim_available()
    assert restarted_rewards == []

    restarted_collection = restarted_equipment.get_collection()
    assert len(
        [
            owned
            for owned in restarted_collection.items
            if owned.definition_id == portal_definition.definition_id
        ]
    ) == 1
    assert (
        restarted_equipment.final_stats(character.asset_id)
        == after_stats
    )


def test_new_session_cannot_duplicate_nonrepeatable_quest_reward(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    quest = _quest(repo)
    inbox_path = tmp_path / "quest_reward_inbox.json"
    equipment = EquipmentService(repo)

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_SESSION_ONE",
    )
    first = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=equipment,
    ).claim_available()
    assert len(first) == 1

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_SESSION_TWO",
    )
    second = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=equipment,
    ).claim_available()
    assert second == []


def test_repeatable_quest_can_reward_each_completion_with_distinct_seed(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    quest = _quest(repo, repeatable=True)
    inbox_path = tmp_path / "quest_reward_inbox.json"
    equipment = EquipmentService(repo)
    service = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=equipment,
    )

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_REPEAT_A",
    )
    first = service.claim_available()
    assert len(first) == 1

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_REPEAT_B",
    )
    second = service.claim_available()
    assert len(second) == 1

    collection = equipment.get_collection()
    first_item = collection.item_by_id(first[0].item_instance_id)
    second_item = collection.item_by_id(second[0].item_instance_id)
    assert first_item is not None
    assert second_item is not None
    assert first_item.generation_seed != second_item.generation_seed


def test_my_stuff_claims_generic_quest_rewards():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    my_stuff = (
        root / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")

    assert "QuestRewardService" in my_stuff
    assert "Quest Reward / 任务奖励" in my_stuff
