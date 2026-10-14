"""The actual encoded family MP4 is private until two explicit parent steps."""
import hashlib
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from studio.family_api import FamilyApplication, build_family_server
from studio.family_movie_media import (
    approved_fingerprint, media_path,
)
from studio.repositories.sqlite import SQLiteStudioRepository

ORIGIN = "https://family.example"
ADULT = "synthetic_parent_release_unlock_secret_0123456789abcdef"
A, B = "synthetic-media-child-a", "synthetic-media-child-b"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"z" * 1024


def app_for(db, root):
    return FamilyApplication(
        SQLiteStudioRepository(db),
        token_hashes={
            "child_a": hashlib.sha256(A.encode()).hexdigest(),
            "child_b": hashlib.sha256(B.encode()).hexdigest(),
        },
        parent_unlock_hash=hashlib.sha256(ADULT.encode()).hexdigest(),
        allowed_origins=(ORIGIN,),
        private_movie_root=root,
    )


def call(app, method, uri, data=None, token=A):
    return app.handle(
        method=method, path=uri,
        authorization="Bearer " + token, origin=ORIGIN,
        body=json.dumps(data).encode() if data is not None else b"",
    )


def decision(film, what):
    return {
        "profile_id": "child_a", "film_id": film["film_id"],
        "revision": film["revision"], "decision": what,
    }


def setup_film(tmp_path):
    db = tmp_path / "family.db"
    root = tmp_path / "movies"
    root.mkdir(mode=0o700)
    app = app_for(db, root)
    hero = call(app, "POST", "/characters", {"display_name": "Sheep"})
    film = call(app, "POST", "/family/films", {
        "schema_version": "1.0",
        "display_name": "A synthetic movie",
        "character_id": hero.payload["character_id"],
        "camera": "follow", "action": "walk", "duration_seconds": 15,
    }).payload
    return app, db, root, film


def write_movie(app, root, film):
    fingerprint = approved_fingerprint(
        app.repository, "child_a", film["film_id"]
    )
    assert fingerprint is not None
    path = media_path(
        root, owner="child_a", film_id=film["film_id"],
        fingerprint=fingerprint, create_dirs=True,
    )
    path.write_bytes(MP4)
    path.chmod(0o600)
    return path


def test_movie_release_requires_exact_parent_review_and_actual_bytes(tmp_path):
    app, db, root, film = setup_film(tmp_path)
    fid = film["film_id"]
    status_uri = f"/family/films/{fid}/media-status"
    release_uri = "/family/movie-releases"
    assert call(app, "GET", status_uri).payload["released_to_child"] is False
    assert call(app, "GET", status_uri, token=B).status == 404
    assert call(app, "POST", release_uri, decision(film, "release"),
                token=ADULT).status == 409

    review = call(app, "POST", "/family/film-reviews", decision(
        film, "approve"), token=ADULT)
    assert review.status == 200 and review.payload["approved_for_private_render"]
    assert call(app, "POST", release_uri, decision(film, "release"),
                token=ADULT).status == 409
    path = write_movie(app, root, film)
    assert call(app, "POST", release_uri, decision(film, "release")).status == 401
    assert call(app, "POST", release_uri, decision(film, "release"),
                token=B).status == 401
    released = call(app, "POST", release_uri, decision(film, "release"), token=ADULT)
    assert released.status == 200 and released.payload["released_to_child"]
    assert released.payload["bytes"] == len(MP4)
    assert call(app, "GET", status_uri, token=B).status == 404
    assert app.private_mp4_for_download(
        authorization="Bearer " + B, film_id=fid, origin=ORIGIN
    ) is None
    assert app.private_mp4_for_download(
        authorization="Bearer " + A, film_id=fid, origin=ORIGIN
    ) == MP4
    assert app.private_mp4_for_download(
        authorization="Bearer " + A, film_id=fid, origin="https://evil.example"
    ) is None

    # Existing byte-level permission persists across private server restarts.
    restarted = app_for(db, root)
    assert restarted.private_mp4_for_download(
        authorization="Bearer " + A, film_id=fid, origin=ORIGIN
    ) == MP4

    # Tampering with an MP4 after release is rejected, not served.
    path.write_bytes(MP4 + b"unreviewed changes")
    assert not call(restarted, "GET", status_uri).payload["released_to_child"]
    assert restarted.private_mp4_for_download(
        authorization="Bearer " + A, film_id=fid, origin=ORIGIN
    ) is None
    path.write_bytes(MP4)
    revoked = call(restarted, "POST", release_uri, decision(
        film, "revoke"), token=ADULT)
    assert revoked.status == 200 and not revoked.payload["released_to_child"]
    assert restarted.private_mp4_for_download(
        authorization="Bearer " + A, film_id=fid, origin=ORIGIN
    ) is None


def test_movie_release_invalidated_by_new_review_and_file_perms(tmp_path):
    app, _db, root, film = setup_film(tmp_path)
    fid = film["film_id"]
    assert call(app, "POST", "/family/film-reviews", decision(
        film, "approve"), token=ADULT).status == 200
    path = write_movie(app, root, film)
    path.chmod(0o644)
    assert call(app, "POST", "/family/movie-releases", decision(
        film, "release"), token=ADULT).status == 409
    path.chmod(0o600)
    assert call(app, "POST", "/family/movie-releases", decision(
        film, "release"), token=ADULT).status == 200
    original = call(app, "GET", f"/family/films/{fid}").payload
    edited = call(app, "PUT", f"/family/films/{fid}", {
        "revision": original["revision"],
        "draft": {**original["draft"], "camera": "close"},
    })
    assert edited.status == 200
    assert app.private_mp4_for_download(
        authorization="Bearer " + A, film_id=fid, origin=ORIGIN
    ) is None
    assert call(app, "POST", "/family/movie-releases", decision(
        film, "release"), token=ADULT).status == 409
    assert call(app, "GET", f"/family/films/{fid}/media-status").payload[
        "released_to_child"] is False


def test_loopback_binary_download_no_cookie_token_or_static_media(tmp_path):
    app, _db, root, film = setup_film(tmp_path)
    assert call(app, "POST", "/family/film-reviews", decision(
        film, "approve"), token=ADULT).status == 200
    write_movie(app, root, film)
    assert call(app, "POST", "/family/movie-releases", decision(
        film, "release"), token=ADULT).status == 200
    server = build_family_server(app)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        uri = f"http://127.0.0.1:{server.server_address[1]}/family/films/{film['film_id']}/download"
        good = Request(uri, headers={
            "Authorization": "Bearer " + A, "Origin": ORIGIN,
        })
        with urlopen(good, timeout=5) as reply:
            assert reply.status == 200
            assert reply.headers["Content-Type"] == "video/mp4"
            assert "attachment" in reply.headers["Content-Disposition"]
            assert reply.headers["Cache-Control"] == "private, no-store"
            assert reply.headers["Access-Control-Allow-Origin"] == ORIGIN
            assert reply.read() == MP4
        for bad_headers in [
            {}, {"Authorization": "Bearer " + B, "Origin": ORIGIN},
            {"Authorization": "Bearer " + A, "Origin": "https://evil.example"},
        ]:
            try:
                urlopen(Request(uri, headers=bad_headers), timeout=5)
            except HTTPError as exc:
                assert exc.code == 404
            else:
                raise AssertionError("A private family MP4 escaped its owner scope")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
