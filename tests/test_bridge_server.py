from __future__ import annotations

import json
import threading
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from studio.bridge.server import (
    BRIDGE_PROTOCOL_VERSION,
    BridgeApplication,
    build_server,
)


def _request(url: str, *, method: str = "GET", payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_bridge_application_health_version_and_session():
    app = BridgeApplication()

    health = app.handle(method="GET", path="/health")
    assert health.status == HTTPStatus.OK
    assert health.payload["ok"] is True
    assert health.payload["service"] == "mini-utopia-bridge"
    assert health.payload["bridge_version"] == BRIDGE_PROTOCOL_VERSION
    assert health.payload["canonical_metadata_owner"] == "python_core_repository"
    assert health.payload["godot_mutation_policy"] == "bridge_only"

    version = app.handle(method="GET", path="/version")
    assert version.status == HTTPStatus.OK
    assert version.payload["api_schema_version"] == "1.0"

    session = app.handle(
        method="POST",
        path="/session",
        body=b'{"client":"godot-test"}',
    )
    assert session.status == HTTPStatus.CREATED
    assert session.payload["client"] == "godot-test"
    assert session.payload["session_id"].startswith("BRIDGE_")


def test_bridge_application_has_structured_errors():
    app = BridgeApplication()

    wrong_method = app.handle(method="POST", path="/health")
    assert wrong_method.status == HTTPStatus.METHOD_NOT_ALLOWED
    assert wrong_method.payload["allowed"] == "GET"

    malformed = app.handle(
        method="POST",
        path="/session",
        body=b"{not-json",
    )
    assert malformed.status == HTTPStatus.BAD_REQUEST
    assert malformed.payload["error"] == "invalid_json"

    missing = app.handle(method="GET", path="/does-not-exist")
    assert missing.status == HTTPStatus.NOT_FOUND
    assert missing.payload["error"] == "not_found"


def test_bridge_http_server_round_trip():
    server = build_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"

    try:
        status, health = _request(base + "/health")
        assert status == 200
        assert health["ok"] is True

        status, session = _request(
            base + "/session",
            method="POST",
            payload={"client": "pytest"},
        )
        assert status == 201
        assert session["client"] == "pytest"
        assert session["session_id"].startswith("BRIDGE_")

        status, error = _request(base + "/nope")
        assert status == 404
        assert error["error"] == "not_found"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
