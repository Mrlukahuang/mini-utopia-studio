import hashlib
import json

from studio.family_api import FamilyApplication
from studio.repositories.sqlite import SQLiteStudioRepository


def application(db):
    return FamilyApplication(
        SQLiteStudioRepository(db),
        token_hashes={
            "child_a": hashlib.sha256(b"fixture-child-a").hexdigest(),
            "child_b": hashlib.sha256(b"fixture-child-b").hexdigest(),
        },
        allowed_origins=("https://family.example",),
    )


def call(app, method, url, payload=None, child="child_a"):
    return app.handle(
        method=method, path=url,
        origin="https://family.example",
        authorization="Bearer " + (
            "fixture-child-a" if child == "child_a" else "fixture-child-b"
        ),
        body=json.dumps(payload).encode() if payload is not None else b"",
    )


def test_private_render_source_reuses_owned_two_heroes_and_handmade_prop(tmp_path):
    db = tmp_path / "render-source.db"
    app = application(db)
    first = call(app, "POST", "/characters", {
        "display_name": "Synthetic Sheep",
        "description": "A child's private biography",
    })
    second = call(app, "POST", "/characters", {
        "display_name": "Synthetic Cat",
    })
    outsider = call(app, "POST", "/characters", {
        "display_name": "Sibling Only",
    }, child="child_b")
    a_id, b_id = first.payload["character_id"], second.payload["character_id"]

    crafted = call(app, "POST", f"/characters/{a_id}/crafted-props", {
        "schema_version": "1.0", "display_name": "My Mint Star Wand",
        "shape": "star", "slot": "weapon_main",
        "color_hex": "#B9E7D0", "accent_color_hex": "#F2C75C",
    })
    assert crafted.status == 201
    item_id = crafted.payload["crafted"]["item_instance_id"]
    assert call(app, "PUT", f"/characters/{a_id}/equipment/weapon_main", {
        "item_instance_id": item_id,
    }).status == 200

    draft = {
        "schema_version": "1.0", "display_name": "Two Adventurers",
        "character_id": a_id, "second_character_id": b_id,
        "camera": "close", "action": "celebrate",
        "duration_seconds": 30,
        "private_story_note": "Confidential child's story idea",
    }
    film = call(app, "POST", "/family/films", draft)
    assert film.status == 201
    fid = film.payload["film_id"]
    endpoint = f"/family/films/{fid}/render-source"

    assert call(app, "GET", endpoint, child="child_b").status == 404
    assert call(app, "POST", endpoint, {}).status == 405
    assert call(app, "GET", endpoint.replace(fid, outsider.payload[
        "character_id"])).status == 404
    result = call(app, "GET", endpoint)
    assert result.status == 200
    data = result.payload
    assert data["source_film_id"] == fid
    assert data["character"]["character_id"] == a_id
    assert data["second_character"]["character_id"] == b_id
    assert data["equipment_runtime"]["character_asset_id"] == a_id
    assert data["second_equipment_runtime"]["character_asset_id"] == b_id
    custom = data["equipment_runtime"]["equipped"]["weapon_main"]
    assert custom["item_instance_id"] == item_id
    assert custom["visual_recipe"]["shape"] == "star"
    assert custom["visual_recipe"]["color_hex"] == "#B9E7D0"
    assert data["director_choices"] == {
        "camera": "close", "action": "celebrate", "duration_seconds": 30
    }
    assert (data["fps"], data["width"], data["height"]) == (2, 480, 270)
    assert "description" not in data["character"]
    assert "private_story_note" not in json.dumps(data)
    assert "A child's private biography" not in json.dumps(data)
    assert "Confidential child's story idea" not in json.dumps(data)
    assert "fixture-child-a" not in json.dumps(data)

    reopened = application(db)
    again = call(reopened, "GET", endpoint)
    assert again.status == 200
    assert again.payload["source_revision"] == "1"
    assert again.payload["equipment_runtime"]["equipped"][
        "weapon_main"]["item_instance_id"] == item_id

    # Current owner and state are rechecked for every export, so past
    # permissions cannot silently survive a parent removing a cast member.
    asset = reopened.repository.get_asset(b_id)
    asset.metadata["family_owner"] = "child_b"
    reopened.repository.save_asset(asset)
    assert call(reopened, "GET", endpoint).status == 404


def test_render_source_reflects_latest_edit_without_new_character(tmp_path):
    app = application(tmp_path / "film-edits.db")
    hero = call(app, "POST", "/characters", {"display_name": "One Sheep"})
    cid = hero.payload["character_id"]
    draft = {
        "schema_version": "1.0", "display_name": "Original Movie",
        "character_id": cid,
        "camera": "follow", "action": "walk", "duration_seconds": 15,
    }
    record = call(app, "POST", "/family/films", draft).payload
    fid = record["film_id"]
    endpoint = f"/family/films/{fid}/render-source"
    original = call(app, "GET", endpoint)
    assert original.status == 200
    assert "second_character" not in original.payload
    assert original.payload["director_choices"]["duration_seconds"] == 15

    edited = call(app, "PUT", f"/family/films/{fid}", {
        "revision": "1",
        "draft": {**draft, "camera": "wide", "duration_seconds": 30},
    })
    assert edited.status == 200
    source = call(app, "GET", endpoint)
    assert source.payload["source_revision"] == "2"
    assert source.payload["director_choices"] == {
        "camera": "wide", "action": "walk", "duration_seconds": 30
    }
    assert source.payload["character"]["character_id"] == cid
