"""Single-family, fail-closed API in front of the canonical Python Core Bridge.

The HTTP listener is LOOPBACK ONLY. A parent-managed HTTPS reverse proxy is
required before any browser access. No tokens or private media belong in Git.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Mapping
from urllib.parse import unquote, urlsplit

from studio.bridge.server import MAX_REQUEST_BODY_BYTES, BridgeApplication

FAMILY_API_VERSION = "1.0"
DEFAULT_FAMILY_PORT = 8767
_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class FamilyPrincipal:
    principal_id: str
    role: str
    token_sha256: str
    character_ids: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.principal_id):
            raise ValueError("Invalid principal ID")
        if self.role not in {"adult", "child"}:
            raise ValueError("Invalid role")
        if not _SHA256.fullmatch(self.token_sha256):
            raise ValueError("Token digest must be lowercase SHA-256")
        if self.role == "child" and not self.character_ids:
            raise ValueError("Child requires assigned characters")
        if any(not cid.startswith("CHAR_") or not _ID.fullmatch(cid)
               for cid in self.character_ids):
            raise ValueError("Invalid character assignment")


@dataclass(frozen=True)
class FamilyResponse:
    status: int
    payload: dict
    headers: dict[str, str] = field(default_factory=dict)


def _valid_origin(origin: str) -> bool:
    if origin != origin.strip() or origin.endswith("/") or "*" in origin:
        return False
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and (port is None or port > 0)
        and parsed.netloc == parsed.netloc.lower()
        and parsed.username is None
        and parsed.password is None
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
    )


class FamilyAPIApplication:
    """Bearer authentication, per-character authorization and CORS boundary."""

    def __init__(
        self,
        *,
        principals: list[FamilyPrincipal],
        allowed_origins: list[str],
        bridge: BridgeApplication | None = None,
        requests_per_minute: int = 120,
    ) -> None:
        if not principals or not any(p.role == "adult" for p in principals):
            raise ValueError("Adult principal required")
        if not allowed_origins or any(not _valid_origin(x) for x in allowed_origins):
            raise ValueError("Explicit HTTPS origins required")
        if len(set(allowed_origins)) != len(allowed_origins):
            raise ValueError("Duplicate origin")
        if len({p.principal_id for p in principals}) != len(principals):
            raise ValueError("Duplicate principal")
        if len({p.token_sha256 for p in principals}) != len(principals):
            raise ValueError("Duplicate token digest")
        owned: set[str] = set()
        for p in principals:
            if p.role == "child":
                if owned.intersection(p.character_ids):
                    raise ValueError("Character belongs to multiple children")
                owned.update(p.character_ids)
        if requests_per_minute < 1:
            raise ValueError("Rate limit must be positive")
        self._principals = tuple(principals)
        self._origins = frozenset(allowed_origins)
        self._bridge = bridge if bridge is not None else BridgeApplication()
        self._limit = requests_per_minute
        self._recent: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> "FamilyAPIApplication":
        raw = os.environ.get("MINI_UTOPIA_FAMILY_ACCESS_JSON", "")
        origins = os.environ.get("MINI_UTOPIA_FAMILY_ORIGINS", "")
        if not raw or not origins:
            raise ValueError("Family access and origin config required")
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("principals"), list):
            raise ValueError("Invalid family access config")
        return cls(
            principals=[
                FamilyPrincipal(
                    principal_id=item["id"],
                    role=item["role"],
                    token_sha256=item["token_sha256"],
                    character_ids=frozenset(item.get("character_ids", [])),
                )
                for item in data["principals"]
            ],
            allowed_origins=origins.split(","),
        )

    def _rate_ok(self, remote_ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            # Loopback proxy should enforce an additional external IP limit.
            if len(self._recent) > 2048:
                self._recent = {
                    ip: q for ip, q in self._recent.items()
                    if q and q[-1] > now - 60
                }
            q = self._recent.setdefault(remote_ip, deque())
            while q and q[0] <= now - 60:
                q.popleft()
            if len(q) >= self._limit:
                return False
            q.append(now)
            return True

    def _principal(self, authorization: str) -> FamilyPrincipal | None:
        if not authorization.startswith("Bearer "):
            return None
        token = authorization[7:]
        if not (16 <= len(token) <= 256) or not token.isascii():
            return None
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        match = None
        for p in self._principals:
            if hmac.compare_digest(digest, p.token_sha256):
                match = p
        return match

    @staticmethod
    def _character_id(route: str) -> str | None:
        parts = route.strip("/").split("/")
        if len(parts) not in {2, 3, 4} or parts[0] != "characters":
            return None
        if len(parts) >= 3 and parts[2] != "equipment":
            return None
        if len(parts) == 4 and not _ID.fullmatch(parts[3]):
            return None
        cid = unquote(parts[1])
        if not cid.startswith("CHAR_") or not _ID.fullmatch(cid):
            return None
        return cid

    def handle(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str] | None = None,
        body: bytes = b"",
        remote_ip: str = "127.0.0.1",
    ) -> FamilyResponse:
        method = method.upper()
        incoming = {key.lower(): value for key, value in (headers or {}).items()}
        origin = incoming.get("origin", "")
        cors = (
            {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
            if origin in self._origins else {}
        )

        def reply(status: int, payload: dict) -> FamilyResponse:
            return FamilyResponse(int(status), payload, dict(cors))

        if origin and origin not in self._origins:
            return reply(HTTPStatus.FORBIDDEN, {"error": "origin_forbidden"})
        route = urlsplit(path).path
        cid = self._character_id(route)
        if route not in {"/health", "/version", "/characters"} and cid is None:
            return reply(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        if method == "OPTIONS":
            requested = incoming.get("access-control-request-method", "").upper()
            header_names = {
                h.strip().lower()
                for h in incoming.get("access-control-request-headers", "").split(",")
                if h.strip()
            }
            if (not origin or requested not in {"GET", "PUT"}
                    or not header_names.issubset({"authorization", "content-type"})):
                return reply(HTTPStatus.FORBIDDEN, {"error": "preflight_denied"})
            response = reply(HTTPStatus.NO_CONTENT, {})
            response.headers.update({
                "Access-Control-Allow-Methods": "GET, PUT",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Max-Age": "600",
            })
            return response

        if not self._rate_ok(remote_ip):
            return reply(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited"})
        principal = self._principal(incoming.get("authorization", ""))
        if principal is None:
            return reply(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        if method not in {"GET", "PUT"} or (method == "PUT" and cid is None):
            return reply(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
        if principal.role == "child" and cid is not None:
            if cid not in principal.character_ids:
                return reply(HTTPStatus.FORBIDDEN, {"error": "character_forbidden"})

        result = self._bridge.handle(method=method, path=route, body=body)
        if route == "/characters" and principal.role == "child" and result.status == 200:
            payload = dict(result.payload)
            payload["characters"] = [
                item for item in payload.get("characters", [])
                if item.get("character_id") in principal.character_ids
            ]
            return reply(result.status, payload)
        return reply(result.status, result.payload)


def _handler_type(application: FamilyAPIApplication):
    class FamilyHandler(BaseHTTPRequestHandler):
        server_version = "MiniUtopiaFamilyAPI"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_PUT(self) -> None:  # noqa: N802
            self._dispatch("PUT")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._dispatch("OPTIONS")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

        def _dispatch(self, method: str) -> None:
            if (len(self.headers.get_all("Authorization", [])) > 1
                    or len(self.headers.get_all("Origin", [])) > 1
                    or self.headers.get("Transfer-Encoding")):
                self._write(FamilyResponse(400, {"error": "invalid_headers"}))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0:
                self._write(FamilyResponse(400, {"error": "invalid_length"}))
                return
            if length > MAX_REQUEST_BODY_BYTES:
                self._write(FamilyResponse(413, {"error": "request_too_large"}))
                return
            body = self.rfile.read(length) if length else b""
            response = application.handle(
                method=method, path=self.path,
                headers={k: v for k, v in self.headers.items()},
                body=body, remote_ip=self.client_address[0],
            )
            self._write(response)

        def _write(self, response: FamilyResponse) -> None:
            data = json.dumps(response.payload, separators=(",", ":")).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            # Never log URLs, tokens, or children's content.
            pass

    return FamilyHandler


def build_family_server(
    application: FamilyAPIApplication, *, port: int = DEFAULT_FAMILY_PORT
) -> ThreadingHTTPServer:
    """Hard-coded loopback; never expose this plain HTTP listener to the LAN."""
    server = ThreadingHTTPServer(("127.0.0.1", port), _handler_type(application))
    server.daemon_threads = True
    return server


def main() -> None:
    application = FamilyAPIApplication.from_environment()
    server = build_family_server(application)
    print("Family API on loopback; approved HTTPS proxy required", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
