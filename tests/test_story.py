from studio.core.enums import StoryMode
from studio.models.asset import Asset
from studio.core.enums import AssetType
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.story_service import StoryService


def test_same_character_can_be_reused_by_multiple_stories(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    char = Asset.create(AssetType.CHARACTER, "胖胖", "pangpang")
    repo.save_asset(char)
    service = StoryService(repo)
    moon = service.create_story(title="Moon", premise="去月球", mode=StoryMode.PLAYGROUND, asset_ids=[char.asset_id])
    ocean = service.create_story(title="Ocean", premise="去海底", mode=StoryMode.PLAYGROUND, asset_ids=[char.asset_id])
    assert moon.asset_ids == ocean.asset_ids == [char.asset_id]
    assert len(repo.list_assets(AssetType.CHARACTER)) == 1
