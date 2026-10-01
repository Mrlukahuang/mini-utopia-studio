from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.repositories.sqlite import SQLiteStudioRepository


def test_repository_filters_asset_types(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    repo.save_asset(Asset.create(AssetType.CHARACTER, "A", "a"))
    repo.save_asset(Asset.create(AssetType.LOCATION, "Moon", "moon"))
    assert len(repo.list_assets()) == 2
    assert len(repo.list_assets(AssetType.CHARACTER)) == 1
    assert repo.list_assets(AssetType.LOCATION)[0].display_name == "Moon"
