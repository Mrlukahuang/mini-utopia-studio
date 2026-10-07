from __future__ import annotations

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
