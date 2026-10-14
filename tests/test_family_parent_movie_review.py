"""A parent must approve the exact private 15/30s film before rendering."""
import hashlib
import json

from studio.family_api import FamilyApplication
from studio.family_private_movie_worker import PrivateMovieError, render_private_movie
from studio.repositories.sqlite import SQLiteStudioRepository


PARENT = "synthetic_parent_film_review_secret_0123456789longvalue"
A = "synthetic-child-a"
B = "synthetic-child-b"


def app_at(path):
    return FamilyApplication(
        SQLiteStudioRepository(path),
        token_hashes={
            "child_a": hashlib.sha256(A.encode()).hexdigest(),
            "child_b": hashlib.sha256(B.encode()).hexdigest(),
        },
        allowed_origins=("https://family.example",),
        parent_unlock_hash=hashlib.sha256(PARENT.encode()).hexdigest(),
    )


def call(app, method, path, payload=None, auth=A):
    return app.handle(
        method=method, path=path, authorization="Bearer " + auth,
        origin="https://family.example",
        body=json.dumps(payload).encode() if payload is not None else b"",
    )


def review_input(film, **changes):
    return {
        "profile_id": "child_a",
        "film_id": film["film_id"], "revision": film["revision"],
        "decision": "approve", **changes,
    }


def test_private_movie_parent_review_is_owner_scoped_and_revocable(tmp_path):
    db = tmp_path / "private-family.db"
    app = app_at(db)
    lead = call(app, "POST", "/characters", {"display_name": "Sheep"})
    other = call(app, "POST", "/characters", {"display_name": "Cat"}, auth=B)
    cid = lead.payload["character_id"]
    draft = {
        "schema_version": "1.0",
        "display_name": "Spring Adventure", "character_id": cid,
        "camera": "wide", "action": "celebrate", "duration_seconds": 30,
        "private_story_note": "Never reveal my note in review status",
    }
    film = call(app, "POST", "/family/films", draft).payload
    status_path = f"/family/films/{film['film_id']}/review"
    assert call(app, "GET", status_path).payload["requires_parent_review"]
    assert call(app, "GET", status_path, auth=B).status == 404
    assert call(app, "PUT", status_path).status == 405
    assert call(app, "POST", "/family/film-reviews", review_input(film)).status == 401
    assert call(app, "POST", "/family/film-reviews",
                review_input(film), auth=B).status == 401
    assert call(app, "POST", "/family/film-reviews", review_input(
        film, profile_id="child_b"), auth=PARENT).status == 404
    assert call(app, "POST", "/family/film-reviews", review_input(
        film, film_id=other.payload["character_id"]), auth=PARENT).status == 400
    assert call(app, "POST", "/family/film-reviews", {
        **review_input(film), "public_url": "https://example.invalid/file"
    }, auth=PARENT).status == 400

    accepted = call(app, "POST", "/family/film-reviews", review_input(film), auth=PARENT)
    assert accepted.status == 200
    assert accepted.payload["approved_for_private_render"] is True
    assert accepted.payload["revision"] == "1"
    assert "private_story_note" not in json.dumps(accepted.payload)
    assert call(app, "GET", status_path).payload["approved_for_private_render"]
    assert call(app, "GET", status_path, auth=B).status == 404
    assert call(app, "GET", f"/family/films/{film['film_id']}").payload["revision"] == "1"

    # Any saved camera/story edit invalidates even the same parent's consent.
    update = call(app, "PUT", f"/family/films/{film['film_id']}", {
        "revision": "1", "draft": {**draft, "camera": "close"}
    })
    assert update.status == 200 and update.payload["revision"] == "2"
    assert call(app, "GET", status_path).payload["requires_parent_review"]
    assert call(app, "POST", "/family/film-reviews", review_input(film),
                auth=PARENT).status == 409
    latest = {"film_id": film["film_id"], "revision": "2"}
    assert call(app, "POST", "/family/film-reviews",
                review_input(latest), auth=PARENT).payload["approved_for_private_render"]
    # A new handmade prop or wardrobe edit makes that exact render stale.
    made = call(app, "POST", f"/characters/{cid}/crafted-props", {
        "schema_version": "1.0", "display_name": "Blue Wand",
        "slot": "weapon_main", "shape": "star",
        "color_hex": "#74B9FF", "accent_color_hex": "#F2C75C",
    })
    assert made.status == 201
    put = call(app, "PUT", f"/characters/{cid}/equipment/weapon_main", {
        "item_instance_id": made.payload["crafted"]["item_instance_id"],
    })
    assert put.status == 200
    assert not call(app, "GET", status_path).payload["approved_for_private_render"]

    assert call(app, "POST", "/family/film-reviews",
                review_input(latest), auth=PARENT).payload["approved_for_private_render"]
    reopened = app_at(db)
    assert call(reopened, "GET", status_path).payload["approved_for_private_render"]
    revoked = call(reopened, "POST", "/family/film-reviews",
                   review_input(latest, decision="revoke"), auth=PARENT)
    assert revoked.status == 200
    assert revoked.payload["requires_parent_review"]
    assert not call(app_at(db), "GET", status_path).payload["approved_for_private_render"]


def test_private_mp4_worker_blocks_without_parent_review_before_launch(tmp_path):
    db = tmp_path / "review-required.db"
    app = app_at(db)
    cid = call(app, "POST", "/characters", {
        "display_name": "Synthetic Sheep",
    }).payload["character_id"]
    film = call(app, "POST", "/family/films", {
        "schema_version": "1.0", "display_name": "Unapproved Film",
        "character_id": cid, "camera": "follow", "action": "walk",
        "duration_seconds": 15,
    }).payload
    project = tmp_path / "project" / "godot"
    project.mkdir(parents=True)
    (project / "project.godot").write_text("config_version=5\n")
    output_dir = tmp_path / "private-out"
    output_dir.mkdir(mode=0o700)
    output = output_dir / "unapproved.mp4"
    try:
        render_private_movie(
            db_path=db, project_dir=project, film_id=film["film_id"],
            owner="child_a", output_path=output,
            runner=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("Rendering must not start without parent review")
            ),
        )
    except PrivateMovieError as exc:
        assert "parent approval" in str(exc)
    else:
        raise AssertionError("Private worker rendered a film without approval")
    assert not output.exists()
