import hashlib
import json

from studio.family_api import FamilyApplication
from studio.repositories.sqlite import SQLiteStudioRepository


def app_for(path):
    return FamilyApplication(
        SQLiteStudioRepository(path),
        token_hashes={
            "child_a": hashlib.sha256(b"synthetic-a").hexdigest(),
            "child_b": hashlib.sha256(b"synthetic-b").hexdigest(),
        },
        allowed_origins=("https://family.example",),
    )


def call(app, method, path, data=None, child="child_a"):
    return app.handle(
        method=method, path=path,
        authorization="Bearer " + (
            "synthetic-a" if child == "child_a" else "synthetic-b"
        ),
        origin="https://family.example",
        body=json.dumps(data).encode() if data is not None else b"",
    )


def film(character_id, **changes):
    return {
        "schema_version": "1.0",
        "display_name": "My Sheep Movie",
        "character_id": character_id,
        "camera": "close",
        "action": "celebrate",
        "duration_seconds": 30,
        "private_story_note": "A moonlit adventure",
        **changes,
    }


def test_child_movies_save_reopen_edit_and_stay_private(tmp_path):
    db = tmp_path / "family-films.db"
    api = app_for(db)
    a = call(api, "POST", "/characters", {"display_name": "Sheep"})
    b = call(api, "POST", "/characters", {"display_name": "Cat"}, child="child_b")
    aid, bid = a.payload["character_id"], b.payload["character_id"]
    path = "/family/films"
    first = call(api, "POST", path, film(aid))
    assert first.status == 201
    doc = first.payload
    fid = doc["film_id"]
    assert fid.startswith("FILM_")
    assert doc["revision"] == "1"
    assert doc["draft"]["duration_seconds"] == 30
    assert doc["draft"]["caption_preset"] == "none"
    assert call(api, "GET", f"{path}/{fid}", child="child_b").status == 404
    assert call(api, "PUT", f"{path}/{fid}", {"revision": "1", "draft": film(bid)},
                child="child_b").status == 404
    assert call(api, "GET", path, child="child_b").payload["films"] == []

    updated = call(api, "PUT", f"{path}/{fid}", {
        "revision": "1",
        "draft": film(aid, display_name="My 15 Second Adventure",
                      camera="wide", action="run", duration_seconds=15),
    })
    assert updated.status == 200
    assert updated.payload["revision"] == "2"
    assert updated.payload["draft"]["camera"] == "wide"
    assert call(api, "PUT", f"{path}/{fid}", {
        "revision": "1", "draft": film(aid),
    }).status == 409

    reopened = app_for(db)
    saved = call(reopened, "GET", f"{path}/{fid}")
    assert saved.status == 200
    assert saved.payload["film_id"] == fid
    assert saved.payload["draft"]["duration_seconds"] == 15
    assert saved.payload["draft"]["private_story_note"] == "A moonlit adventure"
    assert saved.payload["draft"]["caption_preset"] == "none"
    assert [x["film_id"] for x in call(
        reopened, "GET", path
    ).payload["films"]] == [fid]
    assert call(reopened, "GET", path, child="child_b").payload["films"] == []


def test_film_drafts_cannot_borrow_sibling_or_unsafe_content(tmp_path):
    api = app_for(tmp_path / "strict-films.db")
    a = call(api, "POST", "/characters", {"display_name": "Sheep"})
    b = call(api, "POST", "/characters", {"display_name": "Cat"}, child="child_b")
    aid, bid = a.payload["character_id"], b.payload["character_id"]
    for bad, expected in [
        (film(bid), 404),
        (film(aid, second_character_id=bid), 404),
        (film(aid, second_character_id=aid), 404),
        (film(aid, camera="unsafe-camera"), 400),
        (film(aid, caption_preset="unsafe_free_text"), 400),
        (film(aid, caption_preset={"text": "raw words"}), 400),
        (film(aid, duration_seconds=240), 400),
        (film(aid, private_story_note="x" * 281), 400),
        (film(aid, extra_field=True), 400),
    ]:
        assert call(api, "POST", "/family/films", bad).status == expected
    assert call(api, "GET", "/family/films/OTHER_ID").status == 404
