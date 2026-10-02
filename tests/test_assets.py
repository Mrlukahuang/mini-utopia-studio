from studio.core.enums import AssetType
from studio.models.character import CharacterProfile
from studio.services.asset_service import AssetService
from studio.repositories.sqlite import SQLiteStudioRepository


def test_character_asset_has_stable_machine_id(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = AssetService(repo)
    asset = service.create_character(
        name="胖胖",
        description="一只喜欢冒险的大熊猫",
        profile=CharacterProfile(
            character_type="大熊猫",
            age="8",
            appearance="胖胖的",
            personality_traits=["好奇"],
            speaking_tone="温柔",
            native_language="中文",
            english_level=4,
        ),
    )

    assert asset.asset_type == AssetType.CHARACTER
    assert asset.asset_id.startswith("CHAR_")

    saved = repo.get_asset(asset.asset_id)
    assert saved is not None
    assert saved.display_name == "胖胖"
    assert saved.metadata["character_profile"]["character_type"] == "大熊猫"
    assert saved.metadata["character_profile"]["english_level"] == 4


def test_update_character_preserves_permanent_asset_id(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = AssetService(repo)
    original = service.create_character(
        name="Original",
        description="first",
        profile=CharacterProfile(character_type="动物 / Animal"),
    )

    updated = service.update_character(
        asset_id=original.asset_id,
        name="Updated",
        description="second",
        profile=CharacterProfile(character_type="机器人 / Robot"),
    )

    assert updated.asset_id == original.asset_id
    assert repo.get_asset(original.asset_id).display_name == "Updated"
    assert (
        repo.get_asset(original.asset_id)
        .metadata["character_profile"]["character_type"]
        == "机器人 / Robot"
    )


def test_default_character_wearables_are_idempotent(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = AssetService(repo)

    first = service.ensure_default_character_wearables()
    second = service.ensure_default_character_wearables()

    assert first["top"].asset_id == second["top"].asset_id
    assert first["bottom"].asset_id == second["bottom"].asset_id
    assert first["top"].display_name == "White T-Shirt / 白色 T恤"
    assert first["bottom"].display_name == "Blue Jeans / 蓝色牛仔裤"
    assert first["top"].asset_id.startswith("WEAR_")
    assert first["bottom"].asset_id.startswith("WEAR_")


def test_archive_character_is_soft_delete(tmp_path):
    from studio.core.enums import ReviewStatus
    from studio.models.character import CharacterProfile
    from studio.repositories.sqlite import SQLiteStudioRepository
    from studio.services.asset_service import AssetService

    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = AssetService(repo)
    character = service.create_character(
        name="Archive Me",
        description="test",
        profile=CharacterProfile(),
    )

    archived = service.archive_character(character.asset_id)

    assert archived.status == ReviewStatus.ARCHIVED
    assert repo.get_asset(character.asset_id) is not None
    assert repo.get_asset(character.asset_id).status == ReviewStatus.ARCHIVED
