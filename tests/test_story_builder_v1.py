from studio.core.enums import AssetType, StoryMode
from studio.models.asset import Asset
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.story_service import StoryService


def test_structured_story_references_assets_without_copying_them(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")

    traveler = Asset.create(
        AssetType.CHARACTER,
        "Traveler",
        "traveler",
    )
    world = Asset.create(
        AssetType.LOCATION,
        "Newbie Village",
        "newbie-village",
    )
    prop = Asset.create(
        AssetType.PROP,
        "Golden Key",
        "golden-key",
    )
    for asset in (traveler, world, prop):
        repo.save_asset(asset)

    story = StoryService(repo).create_story(
        title="The Hill Key",
        premise="A key on the mountain opens a Portal.",
        mode=StoryMode.CANON,
        universe_id="UNIV_MINI_UTOPIA",
        asset_ids=[
            traveler.asset_id,
            world.asset_id,
            prop.asset_id,
            traveler.asset_id,
        ],
        hook="Arrive in the village.",
        discovery="Find a glowing key.",
        conflict="Skeletons guard the path.",
        adventure="Climb the terraces.",
        twist="The key belongs to the Portal.",
        ending="The Portal opens to the next world.",
    )

    assert story.asset_ids == [
        traveler.asset_id,
        world.asset_id,
        prop.asset_id,
    ]
    assert story.universe_id == "UNIV_MINI_UTOPIA"
    assert story.hook == "Arrive in the village."
    assert story.discovery == "Find a glowing key."
    assert story.conflict == "Skeletons guard the path."
    assert story.adventure == "Climb the terraces."
    assert story.twist == "The key belongs to the Portal."
    assert story.ending == "The Portal opens to the next world."

    assert repo.get_asset(traveler.asset_id) == traveler
    assert repo.get_asset(world.asset_id) == world
    assert repo.get_asset(prop.asset_id) == prop


def test_old_story_payloads_remain_compatible():
    from studio.models.story import Story

    old = Story.model_validate(
        {
            "story_id": "STORY_OLD",
            "title": "Old Story",
            "premise": "Legacy premise",
            "mode": "playground",
            "asset_ids": [],
        }
    )

    assert old.discovery == ""
    assert old.adventure == ""


def test_app_exposes_story_builder_as_creator_page():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "app.py").read_text(encoding="utf-8")
    ui = (
        root / "studio" / "ui" / "creator" / "story_builder.py"
    ).read_text(encoding="utf-8")

    assert '"✍️ Story Builder"' in app
    assert "render_story_builder" in app
    assert "Story Builder v1" in ui
    assert "ARRIVE / Hook" in ui
    assert "DISCOVER" in ui
    assert "PROBLEM" in ui
    assert "ADVENTURE" in ui
    assert "SURPRISE" in ui
    assert "PORTAL / NEXT WORLD" in ui
    assert "asset.asset_id" in ui
