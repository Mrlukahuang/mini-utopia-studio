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


def test_equipment_is_scoped_to_each_child_and_persists(tmp_path):
    database_path = tmp_path / "family_equipment.db"
    repo = SQLiteStudioRepository(database_path)
    app = make_app(repo)

    a = call(app, "POST", "/characters", payload={"display_name": "Pink Sheep"})
    b = call(app, "POST", "/characters", auth=AUTH_B, payload={"display_name": "Blue Cat"})
    assert a.status == 201 and b.status == 201
    cid_a, cid_b = a.payload["character_id"], b.payload["character_id"]

    state_a = call(app, "GET", f"/characters/{cid_a}/equipment")
    state_b = call(app, "GET", f"/characters/{cid_b}/equipment", auth=AUTH_B)
    assert state_a.status == 200 and state_b.status == 200
    assert state_a.payload["character_id"] == cid_a
    assert len(state_a.payload["slots"]) == 9

    # Different starter collections mean item instances cannot be borrowed.
    a_ids = {item["item_instance_id"] for item in state_a.payload["items"]}
    b_ids = {item["item_instance_id"] for item in state_b.payload["items"]}
    assert a_ids and b_ids and a_ids.isdisjoint(b_ids)
    assert repo.get_collection("COLL_DEFAULT") is None

    sword = next(item for item in state_a.payload["items"] if item["slot"] == "weapon_main")
    sword_id = sword["item_instance_id"]
    equipped = call(
        app, "PUT", f"/characters/{cid_a}/equipment/weapon_main",
        payload={"item_instance_id": sword_id},
    )
    assert equipped.status == 200
    assert equipped.payload["runtime"]["equipped"]["weapon_main"]["item_instance_id"] == sword_id

    # Ownership validation happens before ANY equipment access.
    assert call(app, "GET", f"/characters/{cid_a}/equipment", auth=AUTH_B).status == 404
    assert call(
        app, "PUT", f"/characters/{cid_a}/equipment/weapon_main",
        auth=AUTH_B, payload={"item_instance_id": sword_id},
    ).status == 404
    assert call(
        app, "PUT", f"/characters/{cid_b}/equipment/weapon_main",
        auth=AUTH_B, payload={"item_instance_id": sword_id},
    ).status == 400

    for payload in ({}, {"item_instance_id": sword_id, "family_owner": "child_b"},
                    {"item_instance_id": 42}):
        assert call(
            app, "PUT", f"/characters/{cid_a}/equipment/weapon_main",
            payload=payload,
        ).status == 400
    assert call(
        app, "PUT", f"/characters/{cid_a}/equipment/outfit",
        payload={"item_instance_id": None},
    ).status == 400
    assert call(app, "GET", f"/characters/{cid_b}/equipment").status == 404

    reopened = make_app(SQLiteStudioRepository(database_path))
    saved = call(reopened, "GET", f"/characters/{cid_a}/equipment")
    assert saved.status == 200
    assert saved.payload["runtime"]["equipped"]["weapon_main"]["item_instance_id"] == sword_id
    other = call(reopened, "GET", f"/characters/{cid_b}/equipment", auth=AUTH_B)
    assert other.status == 200
    assert "weapon_main" not in other.payload["runtime"]["equipped"]

    unequipped = call(
        reopened, "PUT", f"/characters/{cid_a}/equipment/weapon_main",
        payload={"item_instance_id": None},
    )
    assert unequipped.status == 200
    assert "weapon_main" not in unequipped.payload["runtime"]["equipped"]


def test_equipment_collection_owner_mismatch_is_rejected(tmp_path):
    from studio.services.equipment_service import EquipmentService

    repo = SQLiteStudioRepository(tmp_path / "owners.db")
    own_a = EquipmentService(
        repo, collection_id="COLL_FAMILY_child_a", owner_key="child_a"
    )
    own_a.ensure_starter_collection()
    wrong = EquipmentService(
        repo, collection_id="COLL_FAMILY_child_a", owner_key="child_b"
    )
    with pytest.raises(ValueError, match="owner mismatch"):
        wrong.get_collection()


# Production-facing issuance path: adult presents ONE high-entropy parent
# credential and selects a child; the game receives only a 30-minute token.
PARENT_SECRET = "parent_unlock_secret_very_long_synthetic_value_12345"
PARENT_AUTH = "Bearer " + PARENT_SECRET


def test_parent_unlock_issues_expiring_child_scoped_sessions(tmp_path):
    from studio.family_api import SESSION_TTL_SECONDS

    db = tmp_path / "short_sessions.db"
    repo = SQLiteStudioRepository(db)
    app = FamilyApplication(
        repo,
        token_hashes={
            "child_a": _token_hash("test-child-a-legacy-credential"),
            "child_b": _token_hash("test-child-b-legacy-credential"),
        },
        allowed_origins=(ORIGIN,),
        parent_unlock_hash=_token_hash(PARENT_SECRET),
    )

    created = call(app, "POST", "/characters", auth="Bearer test-child-a-legacy-credential",
                   payload={"display_name": "Sheep"})
    assert created.status == 201
    id_a = created.payload["character_id"]

    missing_parent = call(
        app, "POST", "/family/sessions",
        auth="Bearer test-child-a-legacy-credential",
        payload={"profile_id": "child_a"},
    )
    assert missing_parent.status == 401

    for payload in (
        {}, {"profile_id": "unknown"},
        {"profile_id": "child_a", "family_owner": "child_b"},
        {"profile_id": 99},
    ):
        invalid = call(app, "POST", "/family/sessions",
                       auth=PARENT_AUTH, payload=payload)
        assert invalid.status == 400

    issued = call(app, "POST", "/family/sessions",
                  auth=PARENT_AUTH, payload={"profile_id": "child_a"})
    assert issued.status == 201
    assert issued.payload["expires_in_seconds"] == SESSION_TTL_SECONDS
    assert issued.payload["profile_id"] == "child_a"
    token = issued.payload["access_token"]
    assert len(token) >= 32
    assert PARENT_SECRET not in json.dumps(issued.payload)
    assert app.authenticate(PARENT_AUTH) is None

    short_auth = "Bearer " + token
    own = call(app, "GET", "/characters", auth=short_auth)
    assert own.status == 200
    assert own.payload["characters"][0]["character_id"] == id_a

    issued_b = call(app, "POST", "/family/sessions",
                    auth=PARENT_AUTH, payload={"profile_id": "child_b"})
    assert issued_b.status == 201
    other_auth = "Bearer " + issued_b.payload["access_token"]
    assert call(app, "GET", f"/characters/{id_a}", auth=other_auth).status == 404
    assert call(app, "GET", "/characters", auth=other_auth).payload["characters"] == []

    # Server stores digest only; expiration is enforced without a client clock.
    digest = hashlib.sha256(token.encode()).hexdigest()
    assert digest in app._sessions
    assert token not in app._sessions
    owner, _ = app._sessions[digest]
    app._sessions[digest] = (owner, 0.0)
    assert call(app, "GET", "/characters", auth=short_auth).status == 401
    assert call(app, "GET", "/characters", auth=other_auth).status == 200

    revoked = call(app, "DELETE", "/family/sessions/current", auth=other_auth)
    assert revoked.status == 204
    assert call(app, "GET", "/characters", auth=other_auth).status == 401
    assert call(
        app, "DELETE", "/family/sessions/current",
        auth="Bearer test-child-a-legacy-credential",
    ).status == 403


def test_parent_unlock_invalid_attempts_are_rate_limited_and_secrets_not_logged(tmp_path):
    app = FamilyApplication(
        SQLiteStudioRepository(tmp_path / "rate_limited.db"),
        token_hashes={"child_a": _token_hash("fake_a"), "child_b": _token_hash("fake_b")},
        allowed_origins=(ORIGIN,),
        parent_unlock_hash=_token_hash(PARENT_SECRET),
    )
    for _ in range(5):
        resp = call(app, "POST", "/family/sessions",
                    auth="Bearer wrong_parent_password_for_tests",
                    payload={"profile_id": "child_a"})
        assert resp.status == 401
    limited = call(
        app, "POST", "/family/sessions", auth=PARENT_AUTH,
        payload={"profile_id": "child_a"},
    )
    assert limited.status == 429

    disabled = make_app(SQLiteStudioRepository(tmp_path / "disabled.db"))
    assert call(
        disabled, "POST", "/family/sessions", auth=PARENT_AUTH,
        payload={"profile_id": "child_a"},
    ).status == 503


def test_parent_grants_movie_only_cross_child_cast_and_revoke(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "cast-grants.db")
    parent = "Bearer synthetic_parent_cross_cast_unlock_secret_0123456789"
    app = FamilyApplication(
        repo,
        token_hashes={
            "child_a": _token_hash("a-private-random-token-for-tests"),
            "child_b": _token_hash("b-private-random-token-for-tests"),
        },
        allowed_origins=(ORIGIN,),
        parent_unlock_hash=_token_hash(parent[len("Bearer "):]),
    )
    a = call(app, "POST", "/characters", payload={
        "display_name": "Sheep", "description": "Private child A biography",
        "profile": {"avatar": {
            "species_head_id": "species_head_sheep_v1",
            "surface_color_hex": "#F7B7D2",
        }},
    })
    b = call(app, "POST", "/characters", auth=AUTH_B, payload={
        "display_name": "Cat", "description": "Private child B biography",
        "profile": {"avatar": {
            "species_head_id": "species_head_cat_v1",
            "surface_color_hex": "#B9E7D0",
        }},
    })
    aid, bid = a.payload["character_id"], b.payload["character_id"]
    b_inventory = call(app, "GET", f"/characters/{bid}/equipment", auth=AUTH_B)
    assert b_inventory.status == 200
    crown = next(item for item in b_inventory.payload["items"] if item["slot"] == "headwear")
    equipped = call(app, "PUT", f"/characters/{bid}/equipment/headwear",
                    auth=AUTH_B, payload={"item_instance_id": crown["item_instance_id"]})
    assert equipped.status == 200
    assert call(app, "GET", f"/characters/{bid}").status == 404
    assert call(app, "GET", f"/characters/{bid}/equipment").status == 404
    assert call(app, "GET", "/family/cast-guests").payload["guests"] == []

    approval = {
        "viewer_profile_id": "child_a", "source_profile_id": "child_b",
        "character_id": bid,
    }
    assert call(app, "POST", "/family/cast-grants", payload=approval).status == 401
    assert call(app, "POST", "/family/cast-grants", auth=AUTH_B,
                payload=approval).status == 401
    assert call(app, "POST", "/family/cast-grants", auth=parent,
                payload={**approval, "scope": "edit"}).status == 400
    assert call(app, "POST", "/family/cast-grants", auth=parent,
                payload={**approval, "source_profile_id": "child_a"}).status == 400
    assert call(app, "POST", "/family/cast-grants", auth=parent,
                payload={**approval, "viewer_profile_id": "child_b"}).status == 400
    assert call(app, "POST", "/family/cast-grants", auth=parent,
                payload={**approval, "character_id": aid}).status == 404

    granted = call(app, "POST", "/family/cast-grants", auth=parent,
                   payload=approval)
    assert granted.status == 201
    grant_id = granted.payload["grant_id"]
    assert grant_id.startswith("CAST_")
    assert granted.payload["expires_in_seconds"] == 900

    guests_a = call(app, "GET", "/family/cast-guests")
    guests_b = call(app, "GET", "/family/cast-guests", auth=AUTH_B)
    assert [guest["grant_id"] for guest in guests_a.payload["guests"]] == [grant_id]
    assert guests_b.payload["guests"] == []
    view = call(app, "GET", f"/family/cast-guests/{grant_id}")
    assert view.status == 200
    assert set(view.payload) == {"schema_version", "grant_id", "character",
                                "equipment_runtime"}
    exposed = view.payload["character"]
    assert exposed["character_id"] == bid
    assert exposed["profile"]["avatar"]["species_head_id"] == "species_head_cat_v1"
    assert "description" not in exposed
    assert "revision" not in exposed
    assert "character_profile" not in exposed
    assert "Private child B biography" not in json.dumps(view.payload)
    assert "items" not in view.payload  # no browsing full sibling inventory
    assert view.payload["equipment_runtime"]["equipped"]["headwear"][
        "item_instance_id"] == crown["item_instance_id"]
    assert call(app, "GET", f"/family/cast-guests/{grant_id}",
                auth=AUTH_B).status == 404
    assert call(app, "GET", f"/characters/{bid}").status == 404
    assert call(app, "PUT", f"/characters/{bid}", payload={}).status == 404
    assert call(app, "GET", f"/characters/{bid}/equipment").status == 404
    assert call(app, "DELETE", f"/family/cast-grants/{grant_id}").status == 401
    assert call(app, "DELETE", f"/family/cast-grants/{grant_id}",
                auth=parent).status == 204
    assert call(app, "GET", f"/family/cast-guests/{grant_id}").status == 404
    assert call(app, "GET", "/family/cast-guests").payload["guests"] == []
    assert call(app, "GET", f"/characters/{bid}").status == 404


def test_cross_child_cast_expires_and_server_restart_revokes(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "expire-grant.db")
    parent = "Bearer synthetic_parent_cross_cast_unlock_secret_0123456789"
    def configured():
        return FamilyApplication(
            repo, token_hashes={
                "child_a": _token_hash("a-private-random-token-for-tests"),
                "child_b": _token_hash("b-private-random-token-for-tests"),
            },
            allowed_origins=(ORIGIN,),
            parent_unlock_hash=_token_hash(parent[len("Bearer "):]),
        )
    app = configured()
    b = call(app, "POST", "/characters", auth=AUTH_B,
             payload={"display_name": "Approved guest"})
    bid = b.payload["character_id"]
    approval = {"viewer_profile_id": "child_a",
                "source_profile_id": "child_b", "character_id": bid}
    grant = call(app, "POST", "/family/cast-grants", auth=parent, payload=approval)
    gid = grant.payload["grant_id"]
    viewer, source, cid, _ = app._cast_grants[gid]
    app._cast_grants[gid] = viewer, source, cid, 0.0
    assert call(app, "GET", "/family/cast-guests").payload["guests"] == []
    assert call(app, "GET", f"/family/cast-guests/{gid}").status == 404
    fresh = call(app, "POST", "/family/cast-grants", auth=parent, payload=approval)
    assert fresh.status == 201
    restarted = configured()
    assert call(restarted, "GET", "/family/cast-guests").payload["guests"] == []
    assert call(restarted, "GET",
                f"/family/cast-guests/{fresh.payload['grant_id']}").status == 404
