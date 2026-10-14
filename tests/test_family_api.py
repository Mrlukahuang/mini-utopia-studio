from __future__ import annotations

import hashlib
import json
import threading
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from studio.family_api import FamilyApplication, build_family_server
from studio.models.asset import Asset
from studio.core.enums import AssetType
from studio.repositories.sqlite import SQLiteStudioRepository


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_app(repo):
    return FamilyApplication(
        repo,
        token_hashes={
            "child_a": _token_hash("a-private-random-token-for-tests"),
            "child_b": _token_hash("b-private-random-token-for-tests"),
        },
        allowed_origins=("https://family.example", "http://localhost:8080"),
    )


AUTH_A = "Bearer a-private-random-token-for-tests"
AUTH_B = "Bearer b-private-random-token-for-tests"
ORIGIN = "https://family.example"


def call(app, method, path, auth=AUTH_A, payload=None, origin=ORIGIN):
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    return app.handle(
        method=method, path=path, authorization=auth, body=body, origin=origin
    )


def test_character_creation_ownership_and_persistence_after_restart(tmp_path):
    path = tmp_path / "family.db"
    repo = SQLiteStudioRepository(path)
    app = make_app(repo)

    alpha = call(app, "POST", "/characters", payload={
        "schema_version": "1.0",
        "display_name": "  My Sheep  ",
        "profile": {"avatar": {"species_head_id": "species_head_sheep_v1"}},
    })
    bravo = call(app, "POST", "/characters", auth=AUTH_B, payload={
        "display_name": "My Robot",
        "profile": {"avatar": {"species_head_id": "species_head_robot_v1"}},
    })
    assert alpha.status == 201 and bravo.status == 201
    id_a = alpha.payload["character_id"]
    id_b = bravo.payload["character_id"]
    assert id_a != id_b
    assert alpha.payload["display_name"] == "My Sheep"

    mine_a = call(app, "GET", "/characters")
    mine_b = call(app, "GET", "/characters", auth=AUTH_B)
    assert [entry["character_id"] for entry in mine_a.payload["characters"]] == [id_a]
    assert [entry["character_id"] for entry in mine_b.payload["characters"]] == [id_b]
    assert call(app, "GET", f"/characters/{id_b}").status == 404
    assert call(app, "GET", f"/characters/{id_a}", auth=AUTH_B).status == 404

    # The server must *never* accept legacy unowned records into a child list.
    orphan = Asset.create(AssetType.CHARACTER, "Legacy", "legacy")
    repo.save_asset(orphan)
    assert call(app, "GET", f"/characters/{orphan.asset_id}").status == 404

    # Modify canonical Profile, keep identity and owner, then restart SQLite.
    profile = dict(alpha.payload["profile"])
    profile["avatar"]["hair_color_hex"] = "#F7B7D2"
    update = {
        "schema_version": "1.0",
        "revision": alpha.payload["revision"],
        "display_name": "My Sheep",
        "description": "Little star",
        "profile": profile,
    }
    updated = call(app, "PUT", f"/characters/{id_a}", payload=update)
    assert updated.status == 200
    assert updated.payload["profile"]["avatar"]["hair_color_hex"] == "#F7B7D2"
    assert call(app, "PUT", f"/characters/{id_a}", payload=update).status == 200

    reopened = make_app(SQLiteStudioRepository(path))
    saved = call(reopened, "GET", f"/characters/{id_a}")
    assert saved.status == 200
    assert saved.payload["character_id"] == id_a
    assert saved.payload["description"] == "Little star"
    assert saved.payload["profile"]["avatar"]["hair_color_hex"] == "#F7B7D2"
    assert call(reopened, "GET", f"/characters/{id_b}").status == 404


def test_malformed_cross_child_and_stale_writes_fail_closed(tmp_path):
    app = make_app(SQLiteStudioRepository(tmp_path / "data.db"))

    for header in ("", "Bearer ", "Basic example", AUTH_A + "oops"):
        assert call(app, "GET", "/characters", auth=header).status == 401
    assert call(app, "GET", "/characters", origin="https://untrusted.site").status == 403

    for payload in (
        {"display_name": ""},
        {"display_name": " ", "profile": {}},
        {"schema_version": "9.9", "display_name": "Robot"},
        {"display_name": "Robot", "family_owner": "child_b"},
        {"display_name": "Robot", "profile": {"avatar": {"body_type": "invalid"}}},
    ):
        assert call(app, "POST", "/characters", payload=payload).status == 400

    created = call(app, "POST", "/characters", payload={"display_name": "Cat"})
    cid = created.payload["character_id"]
    payload = {
        "schema_version": "1.0",
        "revision": created.payload["revision"],
        "display_name": "Cat",
        "description": "new description",
        "profile": created.payload["profile"],
    }
    assert call(app, "PUT", f"/characters/{cid}", auth=AUTH_B, payload=payload).status == 404
    assert call(app, "PUT", f"/characters/{cid}", payload={
        **payload, "family_owner": "child_b",
    }).status == 400
    assert call(app, "PUT", f"/characters/{cid}", payload=payload).status == 200
    assert call(app, "PUT", f"/characters/{cid}", payload={
        **payload, "display_name": "Overwrite", "revision": "old_revision",
    }).status == 409
    assert call(app, "GET", "/characters/%2Fother").status == 404


def test_requires_distinct_hashed_keys_and_private_origin(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "data.db")
    with pytest.raises(ValueError):
        FamilyApplication(
            repo,
            token_hashes={"child_a": "secret", "child_b": "secret"},
            allowed_origins=(ORIGIN,),
        )
    with pytest.raises(ValueError):
        FamilyApplication(
            repo,
            token_hashes={"child_a": _token_hash("same"), "child_b": _token_hash("same")},
            allowed_origins=(ORIGIN,),
        )
    with pytest.raises(ValueError):
        FamilyApplication(
            repo,
            token_hashes={"child_a": _token_hash("x"), "child_b": _token_hash("y")},
            allowed_origins=("http://public.example",),
        )
    app = make_app(repo)
    with pytest.raises(ValueError):
        build_family_server(app, host="0.0.0.0")


def _http(url, method="GET", body=None, token=AUTH_A, origin=ORIGIN):
    headers = {"Origin": origin}
    if token:
        headers["Authorization"] = token
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(req, timeout=3) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as error:
        return error.code, dict(error.headers), error.read()


def test_http_auth_cors_and_two_character_roundtrip(tmp_path):
    app = make_app(SQLiteStudioRepository(tmp_path / "http.db"))
    server = build_family_server(app, port=0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:%d" % server.server_port

    try:
        status, headers, data = _http(base + "/characters", token="")
        assert status == HTTPStatus.UNAUTHORIZED
        assert json.loads(data)["error"] == "unauthorized"
        assert headers["Cache-Control"] == "no-store"

        status, headers, data = _http(
            base + "/characters",
            method="POST",
            body={"display_name": "Snow Bunny"},
        )
        assert status == 201
        assert headers["Access-Control-Allow-Origin"] == ORIGIN
        cid = json.loads(data)["character_id"]

        status, headers, data = _http(base + "/characters")
        assert status == 200
        assert json.loads(data)["characters"][0]["character_id"] == cid

        status, headers, data = _http(
            base + "/characters", token=AUTH_B,
        )
        assert status == 200
        assert json.loads(data)["characters"] == []

        status, headers, data = _http(
            base + "/characters", origin="https://attacker.example",
        )
        assert status == 403
        assert "Access-Control-Allow-Origin" not in headers

        status, headers, _ = _http(
            base + "/characters", method="OPTIONS", token="",
        )
        assert status == 204
        assert headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
