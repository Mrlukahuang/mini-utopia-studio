import requests

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.equipment import CreatorCollection
from studio.repositories.supabase import SupabaseStudioRepository


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._json_data


def _repo():
    return SupabaseStudioRepository(
        url="https://example.supabase.co",
        service_role_key="test-key",
        table="studio_records",
    )


def test_save_asset_upserts_record(monkeypatch):
    calls = {}

    def fake_post(url, *, params, headers, json, timeout):
        calls.update(url=url, params=params, headers=headers, json=json, timeout=timeout)
        return FakeResponse(201)

    monkeypatch.setattr(requests, "post", fake_post)
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Nova",
        slug="nova",
    )

    _repo().save_asset(asset)

    assert calls["url"].endswith("/rest/v1/studio_records")
    assert calls["params"]["on_conflict"] == "kind,record_id"
    assert calls["headers"]["Prefer"] == "resolution=merge-duplicates"
    assert calls["json"]["kind"] == "asset"
    assert calls["json"]["record_id"] == asset.asset_id
    assert calls["json"]["data"]["display_name"] == "Nova"


def test_get_asset_reads_json_payload(monkeypatch):
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Nova",
        slug="nova",
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            200,
            [{"data": asset.model_dump(mode="json")}],
        ),
    )

    loaded = _repo().get_asset(asset.asset_id)

    assert loaded is not None
    assert loaded.asset_id == asset.asset_id
    assert loaded.display_name == "Nova"


def test_list_assets_filters_by_asset_type(monkeypatch):
    char = Asset.create(AssetType.CHARACTER, display_name="Nova", slug="nova")
    world = Asset.create(AssetType.LOCATION, display_name="Cloud City", slug="cloud-city")

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            200,
            [
                {"data": char.model_dump(mode="json")},
                {"data": world.model_dump(mode="json")},
            ],
        ),
    )

    loaded = _repo().list_assets(AssetType.CHARACTER)

    assert [asset.asset_id for asset in loaded] == [char.asset_id]



def test_save_collection_uses_collection_record_kind(monkeypatch):
    calls = {}

    def fake_post(url, *, params, headers, json, timeout):
        calls.update(url=url, params=params, headers=headers, json=json, timeout=timeout)
        return FakeResponse(201)

    monkeypatch.setattr(requests, "post", fake_post)
    collection = CreatorCollection(
        collection_id="COLL_DEFAULT",
        owner_key="default_creator",
    )

    _repo().save_collection(collection)

    assert calls["json"]["kind"] == "collection"
    assert calls["json"]["record_id"] == "COLL_DEFAULT"
    assert calls["json"]["name"] == "default_creator"


def test_get_collection_reads_json_payload(monkeypatch):
    collection = CreatorCollection(
        collection_id="COLL_DEFAULT",
        owner_key="default_creator",
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            200,
            [{"data": collection.model_dump(mode="json")}],
        ),
    )

    loaded = _repo().get_collection("COLL_DEFAULT")

    assert loaded is not None
    assert loaded.collection_id == "COLL_DEFAULT"
    assert loaded.owner_key == "default_creator"
