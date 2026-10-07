import json

import pytest
from pydantic import ValidationError

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.quest import (
    QuestDefinition,
    QuestObjective,
    QuestObjectiveType,
    QuestReward,
    QuestRewardType,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.quest_service import QuestService


def _world(repo: SQLiteStudioRepository) -> Asset:
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Newbie Village",
        slug="newbie-village",
    )
    repo.save_asset(world)
    return world


def test_quest_contract_sorts_objectives_and_rejects_duplicate_ids():
    quest = QuestDefinition(
        quest_id="QUEST_TEST",
        title="Training",
        world_asset_id="LOC_WORLD",
        objectives=[
            QuestObjective(
                objective_id="second",
                objective_type=QuestObjectiveType.DEFEAT_ENEMY,
                label="Defeat",
                target_id="training_skeleton_01",
                order=1,
            ),
            QuestObjective(
                objective_id="first",
                objective_type=QuestObjectiveType.GO_TO_LOCATION,
                label="Arrive",
                target_id="LOC_WORLD",
                order=0,
            ),
        ],
    )
    assert [item.objective_id for item in quest.objectives] == [
        "first",
        "second",
    ]

    with pytest.raises(ValidationError):
        QuestDefinition(
            quest_id="QUEST_DUP",
            title="Bad Quest",
            world_asset_id="LOC_WORLD",
            objectives=[
                QuestObjective(
                    objective_id="same",
                    objective_type=QuestObjectiveType.INTERACT,
                    label="One",
                    order=0,
                ),
                QuestObjective(
                    objective_id="same",
                    objective_type=QuestObjectiveType.OPEN_PORTAL,
                    label="Two",
                    order=1,
                ),
            ],
        )


def test_quest_objective_count_and_reward_amount_must_be_positive():
    with pytest.raises(ValidationError):
        QuestObjective(
            objective_id="bad_count",
            objective_type=QuestObjectiveType.COLLECT_ITEM,
            label="Collect",
            target_count=0,
            order=0,
        )

    with pytest.raises(ValidationError):
        QuestReward(
            reward_id="bad_reward",
            reward_type=QuestRewardType.BABY_XP,
            amount=0,
        )


def test_newbie_village_quest_is_authored_as_data_and_persists(tmp_path):
    db_path = tmp_path / "studio.db"
    repo = SQLiteStudioRepository(db_path)
    world = _world(repo)

    quest = QuestService(repo).create_newbie_village_training_quest(
        world_asset_id=world.asset_id,
        universe_id="UNIV_MINI_UTOPIA",
    )

    assert quest.world_asset_id == world.asset_id
    assert [item.objective_type.value for item in quest.objectives] == [
        "go_to_location",
        "defeat_enemy",
        "collect_item",
        "open_portal",
    ]
    assert quest.objectives[1].target_id == "training_skeleton_01"
    assert quest.objectives[2].target_id == "reward_bone_buckler"
    assert [reward.reward_type.value for reward in quest.rewards] == [
        "baby_bond",
        "unlock",
    ]

    # The runtime contract is plain JSON data; no quest-specific Godot code is
    # needed to serialize this definition.
    encoded = json.dumps(quest.runtime_payload())
    assert "training_skeleton_01" in encoded
    assert "newbie_village_portal" in encoded

    reloaded_repo = SQLiteStudioRepository(db_path)
    reloaded = QuestService(reloaded_repo).get_quest(quest.quest_id)
    assert reloaded == quest
    assert QuestService(reloaded_repo).list_quests() == [quest]


def test_quest_service_rejects_unknown_or_non_world_asset(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    character = Asset.create(
        AssetType.CHARACTER,
        display_name="Not a World",
        slug="not-a-world",
    )
    repo.save_asset(character)

    objective = QuestObjective(
        objective_id="arrive",
        objective_type=QuestObjectiveType.GO_TO_LOCATION,
        label="Arrive",
        order=0,
    )

    with pytest.raises(ValueError, match="Unknown Quest world_asset_id"):
        QuestService(repo).create_quest(
            title="Missing World",
            world_asset_id="LOC_MISSING",
            objectives=[objective],
        )

    with pytest.raises(ValueError, match="Location"):
        QuestService(repo).create_quest(
            title="Wrong Asset",
            world_asset_id=character.asset_id,
            objectives=[objective],
        )
