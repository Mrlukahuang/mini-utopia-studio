from __future__ import annotations

import json
from http import HTTPStatus

from studio.bridge.characters import (
    BRIDGE_CHARACTER_SCHEMA_VERSION,
    CharacterBridgeReader,
)
from studio.bridge.server import BridgeApplication
from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.avatar import AvatarAppearance, BodyType
from studio.models.character import CharacterProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.asset_service import AssetService


def _seed_characters(db_path):
    repo = SQLiteStudioRepository(db_path)

    custom_profile = CharacterProfile(
        character_type="动物 / Animal",
        age="8",
        appearance="Pink cat hero",
        personality_traits=["勇敢 / Brave"],
        speaking_tone="轻快 / Bright",
        native_language="中文 / Chinese",
        english_level=5,
        avatar=AvatarAppearance(
            customized=True,
            body_type=BodyType.CHUBBY,
            species_head_id="species_head_cat_v1",
            surface_type="fur",
            surface_color_hex="#F7B7D2",
            eye_style_id="eyes_cat_v1",
            eye_color_hex="#BDE3F5",
            hair_style_id="hair_ponytail_v1",
            hair_color_hex="#5B4036",
        ),
    )
    custom = AssetService(repo).create_character(
        name="Mimi",
        description="A brave cat hero.",
        profile=custom_profile,
    )

    legacy = Asset.create(
        AssetType.CHARACTER,
        display_name="Legacy Hero",
        slug="legacy-hero",
        metadata={
            "character_profile": {
                "schema_version": "1.2",
                "character_type": "Human",
                "hair_or_fur_color_hex": "#112233",
                "eyes": {"color_hex": "#445566"},
            }
        },
    )
    repo.save_asset(legacy)

    archived = Asset.create(
        AssetType.CHARACTER,
        display_name="Archived Hero",
        slug="archived-hero",
        metadata={"character_profile": {}},
    )
    archived.status = ReviewStatus.ARCHIVED
    repo.save_asset(archived)

    return custom, legacy, archived


def test_character_read_contract_survives_sqlite_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    custom, legacy, archived = _seed_characters(db_path)

    restarted = SQLiteStudioRepository(db_path)
    reader = CharacterBridgeReader(restarted)

    listed = reader.list_characters()
    listed_ids = {item["character_id"] for item in listed}

    assert custom.asset_id in listed_ids
    assert legacy.asset_id in listed_ids
    assert archived.asset_id not in listed_ids

    payload = reader.get_character(custom.asset_id)
    assert payload is not None
    assert payload["schema_version"] == BRIDGE_CHARACTER_SCHEMA_VERSION
    assert payload["character_id"] == custom.asset_id
    assert payload["display_name"] == "Mimi"
    assert payload["revision"]
    avatar = payload["profile"]["avatar"]
    assert avatar["body_type"] == "chubby"
    assert avatar["species_head_id"] == "species_head_cat_v1"
    assert avatar["surface_type"] == "fur"
    assert avatar["surface_color_hex"] == "#F7B7D2"
    assert avatar["eye_style_id"] == "eyes_cat_v1"
    assert avatar["eye_color_hex"] == "#BDE3F5"
    assert avatar["hair_style_id"] == "hair_ponytail_v1"
    assert avatar["hair_color_hex"] == "#5B4036"

    legacy_payload = reader.get_character(legacy.asset_id)
    assert legacy_payload is not None
    legacy_avatar = legacy_payload["profile"]["avatar"]
    assert legacy_avatar["customized"] is False
    assert legacy_avatar["body_type"] == "standard"
    assert legacy_avatar["species_head_id"] == "species_head_human_v1"
    assert legacy_avatar["eye_style_id"] == "eyes_round_soft_v1"
    assert legacy_avatar["hair_style_id"] == "hair_none"

    # Archived records stay addressable by stable ID for continuity/debugging.
    archived_payload = reader.get_character(archived.asset_id)
    assert archived_payload is not None
    assert archived_payload["review_status"] == "archived"


def test_bridge_character_get_and_list_routes(tmp_path):
    db_path = tmp_path / "studio.db"
    custom, legacy, _archived = _seed_characters(db_path)
    reader = CharacterBridgeReader(SQLiteStudioRepository(db_path))
    app = BridgeApplication(character_reader_factory=lambda: reader)

    listing = app.handle(method="GET", path="/characters")
    assert listing.status == HTTPStatus.OK
    assert listing.payload["schema_version"] == "1.0"
    ids = {
        item["character_id"]
        for item in listing.payload["characters"]
    }
    assert custom.asset_id in ids
    assert legacy.asset_id in ids

    detail = app.handle(
        method="GET",
        path=f"/characters/{custom.asset_id}",
    )
    assert detail.status == HTTPStatus.OK
    assert detail.payload["character_id"] == custom.asset_id
    assert detail.payload["profile"]["avatar"]["body_type"] == "chubby"

    missing = app.handle(
        method="GET",
        path="/characters/CHAR_DOES_NOT_EXIST",
    )
    assert missing.status == HTTPStatus.NOT_FOUND
    assert missing.payload["error"] == "character_not_found"

    wrong_method = app.handle(
        method="POST",
        path=f"/characters/{custom.asset_id}",
    )
    assert wrong_method.status == HTTPStatus.METHOD_NOT_ALLOWED


def test_bridge_character_routes_report_repository_unavailable():
    def broken_reader():
        raise RuntimeError("do not leak this internal detail")

    app = BridgeApplication(character_reader_factory=broken_reader)
    response = app.handle(method="GET", path="/characters")

    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.payload == {
        "error": "repository_unavailable",
        "message": "Canonical Creator repository is unavailable.",
    }



def _put_payload(contract: dict, *, hair_style_id: str) -> dict:
    profile = json.loads(json.dumps(contract["profile"]))
    profile["avatar"]["customized"] = True
    profile["avatar"]["hair_style_id"] = hair_style_id
    return {
        "schema_version": "1.0",
        "revision": contract["revision"],
        "display_name": contract["display_name"],
        "description": contract["description"],
        "profile": profile,
    }


def test_bridge_character_put_updates_same_id_and_survives_restart(tmp_path):
    db_path = tmp_path / "studio.db"
    custom, _legacy, _archived = _seed_characters(db_path)

    repo = SQLiteStudioRepository(db_path)
    asset = repo.get_asset(custom.asset_id)
    assert asset is not None
    asset.metadata["continuity_note"] = "preserve-me"
    repo.save_asset(asset)

    reader = CharacterBridgeReader(repo)
    before = reader.get_character(custom.asset_id)
    assert before is not None
    payload = _put_payload(before, hair_style_id="hair_bob_v1")

    app = BridgeApplication(character_reader_factory=lambda: reader)
    response = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=json.dumps(payload).encode("utf-8"),
    )

    assert response.status == HTTPStatus.OK
    assert response.payload["character_id"] == custom.asset_id
    assert response.payload["revision"] != before["revision"]
    assert (
        response.payload["profile"]["avatar"]["hair_style_id"]
        == "hair_bob_v1"
    )

    restarted = SQLiteStudioRepository(db_path)
    persisted = CharacterBridgeReader(restarted).get_character(
        custom.asset_id
    )
    assert persisted is not None
    assert persisted["character_id"] == custom.asset_id
    assert (
        persisted["profile"]["avatar"]["hair_style_id"]
        == "hair_bob_v1"
    )

    raw_asset = restarted.get_asset(custom.asset_id)
    assert raw_asset is not None
    assert raw_asset.metadata["continuity_note"] == "preserve-me"

    matches = [
        item
        for item in restarted.list_assets(AssetType.CHARACTER)
        if item.asset_id == custom.asset_id
    ]
    assert len(matches) == 1


def test_bridge_character_put_identical_replay_is_idempotent(tmp_path):
    db_path = tmp_path / "studio.db"
    custom, _legacy, _archived = _seed_characters(db_path)
    repo = SQLiteStudioRepository(db_path)
    reader = CharacterBridgeReader(repo)
    app = BridgeApplication(character_reader_factory=lambda: reader)

    before = reader.get_character(custom.asset_id)
    assert before is not None
    payload = _put_payload(before, hair_style_id="hair_bob_v1")
    body = json.dumps(payload).encode("utf-8")

    first = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=body,
    )
    assert first.status == HTTPStatus.OK
    first_revision = first.payload["revision"]

    # Replay the exact same Save with the now-stale original revision.
    second = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=body,
    )
    assert second.status == HTTPStatus.OK
    assert second.payload["character_id"] == custom.asset_id
    assert second.payload["revision"] == first_revision

    matches = [
        item
        for item in repo.list_assets(AssetType.CHARACTER)
        if item.asset_id == custom.asset_id
    ]
    assert len(matches) == 1


def test_bridge_character_put_rejects_stale_conflicting_save(tmp_path):
    db_path = tmp_path / "studio.db"
    custom, _legacy, _archived = _seed_characters(db_path)
    repo = SQLiteStudioRepository(db_path)
    reader = CharacterBridgeReader(repo)
    app = BridgeApplication(character_reader_factory=lambda: reader)

    before = reader.get_character(custom.asset_id)
    assert before is not None

    first_payload = _put_payload(
        before,
        hair_style_id="hair_bob_v1",
    )
    first = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=json.dumps(first_payload).encode("utf-8"),
    )
    assert first.status == HTTPStatus.OK

    stale_payload = _put_payload(
        before,
        hair_style_id="hair_short_v1",
    )
    stale = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=json.dumps(stale_payload).encode("utf-8"),
    )

    assert stale.status == HTTPStatus.CONFLICT
    assert stale.payload["error"] == "revision_conflict"
    assert stale.payload["character_id"] == custom.asset_id
    assert stale.payload["current_revision"] == first.payload["revision"]

    current = reader.get_character(custom.asset_id)
    assert current is not None
    assert (
        current["profile"]["avatar"]["hair_style_id"]
        == "hair_bob_v1"
    )


def test_bridge_character_put_validates_contract_and_path_owns_id(tmp_path):
    db_path = tmp_path / "studio.db"
    custom, _legacy, _archived = _seed_characters(db_path)
    repo = SQLiteStudioRepository(db_path)
    reader = CharacterBridgeReader(repo)
    app = BridgeApplication(character_reader_factory=lambda: reader)

    before = reader.get_character(custom.asset_id)
    assert before is not None
    payload = _put_payload(before, hair_style_id="hair_bob_v1")

    bad_schema = dict(payload)
    bad_schema["schema_version"] = "2.0"
    response = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=json.dumps(bad_schema).encode("utf-8"),
    )
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.payload["error"] == "invalid_character_update"

    with_foreign_id = dict(payload)
    with_foreign_id["character_id"] = "CHAR_SHOULD_NOT_BE_ACCEPTED"
    response = app.handle(
        method="PUT",
        path=f"/characters/{custom.asset_id}",
        body=json.dumps(with_foreign_id).encode("utf-8"),
    )
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.payload["error"] == "invalid_character_update"

    missing = app.handle(
        method="PUT",
        path="/characters/CHAR_DOES_NOT_EXIST",
        body=json.dumps(payload).encode("utf-8"),
    )
    assert missing.status == HTTPStatus.NOT_FOUND
    assert missing.payload["error"] == "character_not_found"
