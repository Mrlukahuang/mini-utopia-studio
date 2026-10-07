from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from studio.core.ids import new_id
from studio.core.product_boundary import (
    CANONICAL_METADATA_OWNER,
    GODOT_CREATOR_MUTATION_POLICY,
)


BRIDGE_PROTOCOL_VERSION = "1.0"
BRIDGE_SERVICE_NAME = "mini-utopia-bridge"
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 8765
MAX_REQUEST_BODY_BYTES = 64 * 1024


@dataclass(frozen=True)
class BridgeResponse:
    status: int
    payload: dict[str, Any]


class BridgeApplication:
    """Dependency-free request router for the local Godot ↔ Python Bridge."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def handle(
        self,
        *,
        method: str,
        path: str,
        body: bytes = b"",
    ) -> BridgeResponse:
        method = method.upper()
        route = urlsplit(path).path

        if route == "/health":
            if method != "GET":
                return self._method_not_allowed("GET")
            return BridgeResponse(
                status=HTTPStatus.OK,
                payload={
                    "ok": True,
                    "service": BRIDGE_SERVICE_NAME,
                    "bridge_version": BRIDGE_PROTOCOL_VERSION,
                    "canonical_metadata_owner": CANONICAL_METADATA_OWNER,
                    "godot_mutation_policy": GODOT_CREATOR_MUTATION_POLICY,
                },
            )

        if route == "/version":
            if method != "GET":
                return self._method_not_allowed("GET")
            return BridgeResponse(
                status=HTTPStatus.OK,
                payload={
                    "service": BRIDGE_SERVICE_NAME,
                    "bridge_version": BRIDGE_PROTOCOL_VERSION,
                    "api_schema_version": "1.0",
                    "canonical_metadata_owner": CANONICAL_METADATA_OWNER,
                },
            )

        if route == "/session":
            if method != "POST":
                return self._method_not_allowed("POST")
            parsed = self._parse_json_object(body)
            if isinstance(parsed, BridgeResponse):
                return parsed

            client = str(parsed.get("client") or "godot").strip() or "godot"
            session_id = new_id("BRIDGE")
            session = {
                "session_id": session_id,
                "client": client,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "bridge_version": BRIDGE_PROTOCOL_VERSION,
            }
            self._sessions[session_id] = session
            return BridgeResponse(
                status=HTTPStatus.CREATED,
                payload=session,
            )

        return BridgeResponse(
            status=HTTPStatus.NOT_FOUND,
            payload={
                "error": "not_found",
                "message": f"Unknown Bridge route: {route}",
            },
        )

    @staticmethod
    def _parse_json_object(body: bytes) -> dict[str, Any] | BridgeResponse:
        if not body:
            return {}
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return BridgeResponse(
                status=HTTPStatus.BAD_REQUEST,
                payload={
                    "error": "invalid_json",
                    "message": "Request body must be valid UTF-8 JSON.",
                },
            )
        if not isinstance(value, dict):
            return BridgeResponse(
                status=HTTPStatus.BAD_REQUEST,
                payload={
                    "error": "invalid_json_shape",
                    "message": "Request JSON must be an object.",
                },
            )
        return value

    @staticmethod
    def _method_not_allowed(allowed: str) -> BridgeResponse:
        return BridgeResponse(
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            payload={
                "error": "method_not_allowed",
                "allowed": allowed,
            },
        )


def _handler_type(application: BridgeApplication):
    class BridgeHTTPRequestHandler(BaseHTTPRequestHandler):
        server_version = "MiniUtopiaBridge"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._dispatch("PUT")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

        def _dispatch(self, method: str) -> None:
            raw_length = self.headers.get("Content-Length", "0")
            try:
                content_length = int(raw_length)
            except ValueError:
                content_length = 0

            if content_length > MAX_REQUEST_BODY_BYTES:
                self._write_json(
                    BridgeResponse(
                        status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        payload={
                            "error": "request_too_large",
                            "max_bytes": MAX_REQUEST_BODY_BYTES,
                        },
                    )
                )
                return

            body = self.rfile.read(content_length) if content_length else b""
            response = application.handle(
                method=method,
                path=self.path,
                body=body,
            )
            self._write_json(response)

        def _write_json(self, response: BridgeResponse) -> None:
            data = json.dumps(
                response.payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            self.send_response(int(response.status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            # Keep local Creator logs readable. Tests do not depend on access logs.
            if os.getenv("MINI_UTOPIA_BRIDGE_ACCESS_LOG") == "1":
                super().log_message(format, *args)

    return BridgeHTTPRequestHandler


def build_server(
    *,
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
    application: BridgeApplication | None = None,
) -> ThreadingHTTPServer:
    app = application or BridgeApplication()
    return ThreadingHTTPServer((host, port), _handler_type(app))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local Mini Utopia Godot ↔ Python Bridge."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MINI_UTOPIA_BRIDGE_HOST", DEFAULT_BRIDGE_HOST),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(
            os.getenv(
                "MINI_UTOPIA_BRIDGE_PORT",
                str(DEFAULT_BRIDGE_PORT),
            )
        ),
    )
    args = parser.parse_args()

    server = build_server(host=args.host, port=args.port)
    host, port = server.server_address[:2]
    print(
        f"{BRIDGE_SERVICE_NAME} v{BRIDGE_PROTOCOL_VERSION} "
        f"listening on http://{host}:{port}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
