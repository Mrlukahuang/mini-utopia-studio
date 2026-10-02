from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.reference import ReferenceCharacterConfig
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.reference_character_service import ReferenceCharacterService
from studio.storage.local import LocalObjectStorage


def _character(name: str, height_cm: float):
    profile = CharacterProfile(height_cm=height_cm)
    return Asset.create(
        AssetType.CHARACTER,
        display_name=name,
        slug=name.lower(),
        metadata={"character_profile": profile.model_dump(mode="json")},
    )


def test_reference_character_service_roundtrip(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = ReferenceCharacterService(repo, storage)

    one = _character("One", 110)
    two = _character("Two", 140)
    repo.save_asset(one)
    repo.save_asset(two)

    saved = service.save(
        ReferenceCharacterConfig(
            character_asset_ids=[one.asset_id, two.asset_id]
        )
    )
    loaded = service.load()

    assert loaded == saved
    assert loaded.character_asset_ids == [one.asset_id, two.asset_id]


def test_reference_character_service_filters_for_height(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = ReferenceCharacterService(repo, storage)

    with_height = _character("Tall", 140)
    without_height = Asset.create(
        AssetType.CHARACTER,
        display_name="Unknown",
        slug="unknown",
        metadata={"character_profile": CharacterProfile().model_dump(mode="json")},
    )
    repo.save_asset(with_height)
    repo.save_asset(without_height)

    eligible = service.eligible_characters()

    assert [asset.asset_id for asset in eligible] == [with_height.asset_id]


def test_reference_character_service_resolves_anchor_heights(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = ReferenceCharacterService(repo, storage)

    one = _character("One", 110)
    two = _character("Two", 140)
    repo.save_asset(one)
    repo.save_asset(two)
    service.save(
        ReferenceCharacterConfig(
            character_asset_ids=[one.asset_id, two.asset_id]
        )
    )

    config, assets, heights = service.resolved_anchors()

    assert [asset.display_name for asset in assets] == ["One", "Two"]
    assert heights == [110.0, 140.0]
    assert config.height_bounds(heights) == (55.0, 280.0)


def test_reference_character_service_rejects_anchor_without_height(tmp_path):
    import pytest

    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = ReferenceCharacterService(repo, storage)

    with_height = _character("Measured", 140)
    without_height = Asset.create(
        AssetType.CHARACTER,
        display_name="Unmeasured",
        slug="unmeasured",
        metadata={"character_profile": CharacterProfile().model_dump(mode="json")},
    )
    repo.save_asset(with_height)
    repo.save_asset(without_height)

    with pytest.raises(ValueError):
        service.save(
            ReferenceCharacterConfig(
                character_asset_ids=[with_height.asset_id, without_height.asset_id]
            )
        )


def test_reference_character_service_handles_stale_height_safely(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = ReferenceCharacterService(repo, storage)

    one = _character("One", 110)
    two = _character("Two", 140)
    repo.save_asset(one)
    repo.save_asset(two)
    service.save(
        ReferenceCharacterConfig(
            character_asset_ids=[one.asset_id, two.asset_id]
        )
    )

    two.metadata["character_profile"]["height_cm"] = None
    repo.save_asset(two)

    assert service.resolved_anchors() is None
