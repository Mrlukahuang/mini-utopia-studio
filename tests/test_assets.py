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
        profile=CharacterProfile(species="大熊猫", personality=["好奇"]),
    )
    assert asset.asset_type == AssetType.CHARACTER
    assert asset.asset_id.startswith("CHAR_")
    saved = repo.get_asset(asset.asset_id)
    assert saved is not None
    assert saved.display_name == "胖胖"
