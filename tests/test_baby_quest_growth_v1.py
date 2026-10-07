import json

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.quest import (
    QuestObjective,
    QuestObjectiveType,
    QuestReward,
    QuestRewardType,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.baby_service import BabyService
from studio.services.equipment_service import EquipmentService
from studio.services.quest_reward_service import QuestRewardService
from studio.services.quest_service import QuestService


def _quest(repo: SQLiteStudioRepository, *, repeatable: bool = False):
    world = Asset.create(
        AssetType.LOCATION,
        display_name="Baby Growth World",
        slug="baby-growth-world",
    )
    repo.save_asset(world)
    return QuestService(repo).create_quest(
        title="Grow Together",
        world_asset_id=world.asset_id,
        objectives=[
            QuestObjective(
                objective_id="finish",
                objective_type=QuestObjectiveType.INTERACT,
                label="Finish together",
                order=0,
            )
        ],
        rewards=[
            QuestReward(
                reward_id="baby_xp",
                reward_type=QuestRewardType.BABY_XP,
                amount=20,
            ),
            QuestReward(
                reward_id="baby_bond",
                reward_type=QuestRewardType.BABY_BOND,
                amount=7,
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
                        "session_id": "PLAY_BABY_GROWTH",
                        "character_asset_id": "CHAR_GROWTH",
                        "created_at": "1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_quest_rewards_grow_active_baby_and_cross_level_threshold(tmp_path):
    db_path = tmp_path / "studio.db"
    inbox_path = tmp_path / "quest_reward_inbox.json"
    repo = SQLiteStudioRepository(db_path)
    babies = BabyService(repo)
    roster = babies.create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    baby_id = roster.active_baby_id
    assert baby_id is not None

    babies.add_xp(baby_id=baby_id, amount=90)
    babies.add_bond(baby_id=baby_id, amount=2)
    quest = _quest(repo)
    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_BABY_A",
    )

    claims = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=EquipmentService(repo),
        babies=babies,
    ).claim_baby_growth()

    assert [claim.reward_type for claim in claims] == [
        QuestRewardType.BABY_XP,
        QuestRewardType.BABY_BOND,
    ]
    active = babies.active_baby()
    assert active is not None
    assert active.baby_id == baby_id
    assert active.xp == 110
    assert active.bond == 9
    assert active.level == 2

    runtime = babies.runtime_spec()
    assert runtime is not None
    assert runtime.level == 2
    assert runtime.xp == 110
    assert runtime.bond == 9

    # Same completion cannot grow the Baby again.
    assert QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=EquipmentService(repo),
        babies=babies,
    ).claim_baby_growth() == []
    assert babies.active_baby().xp == 110
    assert babies.active_baby().bond == 9

    # Full restart preserves growth and idempotency.
    restarted_repo = SQLiteStudioRepository(db_path)
    restarted_babies = BabyService(restarted_repo)
    restarted = restarted_babies.active_baby()
    assert restarted is not None
    assert (restarted.level, restarted.xp, restarted.bond) == (2, 110, 9)
    assert QuestRewardService(
        restarted_repo,
        inbox_path=inbox_path,
        equipment=EquipmentService(restarted_repo),
        babies=restarted_babies,
    ).claim_baby_growth() == []


def test_baby_rewards_wait_until_an_active_baby_exists(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    inbox_path = tmp_path / "quest_reward_inbox.json"
    quest = _quest(repo)
    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_DONE_NO_BABY",
    )

    service = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=EquipmentService(repo),
        babies=BabyService(repo),
    )
    assert service.claim_baby_growth() == []

    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Late Nova",
        species_id="star_baby",
    )
    recovered = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=EquipmentService(repo),
        babies=babies,
    ).claim_baby_growth()
    assert len(recovered) == 2
    assert babies.active_baby().xp == 20
    assert babies.active_baby().bond == 7


def test_repeatable_quest_grows_baby_once_per_completion(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    inbox_path = tmp_path / "quest_reward_inbox.json"
    babies = BabyService(repo)
    babies.create_initial_baby(
        display_name="Repeat Nova",
        species_id="star_baby",
    )
    quest = _quest(repo, repeatable=True)
    service = QuestRewardService(
        repo,
        inbox_path=inbox_path,
        equipment=EquipmentService(repo),
        babies=babies,
    )

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_REPEAT_ONE",
    )
    assert len(service.claim_baby_growth()) == 2

    _write_completion(
        inbox_path,
        quest_id=quest.quest_id,
        completion_id="QUEST_REPEAT_TWO",
    )
    assert len(service.claim_baby_growth()) == 2

    active = babies.active_baby()
    assert active is not None
    assert active.xp == 40
    assert active.bond == 14


def test_baby_growth_is_child_visible_and_smoke_buttons_are_gone():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    my_baby = (
        root / "studio" / "ui" / "creator" / "my_baby.py"
    ).read_text(encoding="utf-8")
    my_stuff = (
        root / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")
    godot = (
        root / "godot" / "scripts" / "baby_follow_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "Quest Growth" in my_baby
    assert "Growth Smoke Controls" not in my_baby
    assert "Baby Growth / 宝宝成长" in my_stuff
    assert "claim_baby_growth()" in my_stuff
    assert " · Lv." in godot
