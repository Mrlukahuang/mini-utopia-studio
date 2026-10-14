"""Private, profile-scoped Character API for Mini Utopia family devices.

This is a distinct service from the unauthenticated *loopback-only* dev Bridge.
Do not expose the local Bridge to the internet or place service-role credentials
in an exported Godot Web bundle. TLS must terminate at a trusted reverse proxy.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal, Mapping
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from studio.bridge.characters import CharacterBridgeReader
from studio.bridge.equipment import EquipmentBridgeGateway
from studio.bridge.errors import CharacterRevisionConflict, CharacterWriteValidationError
from studio.bridge.server import BridgeResponse, MAX_REQUEST_BODY_BYTES
from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.repositories.base import StudioRepository
from studio.services.asset_service import slugify


class FamilyCharacterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    profile: CharacterProfile = Field(default_factory=CharacterProfile)

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("A visible character name is required")
        return name


SESSION_TTL_SECONDS = 1800
PARENT_FAILURE_WINDOW_SECONDS = 60
PARENT_FAILURE_LIMIT = 5


class FamilyApplication:
    """Family owner isolation applies before any repository read or write.

    Token digests are provisioned by an adult on the SERVER, never in GitHub or
    the Web client source. A bearer token identifies one child profile only.
    """

    def __init__(
        self,
        repository: StudioRepository,
        *,
        token_hashes: Mapping[str, str],
        allowed_origins: tuple[str, ...],
        parent_unlock_hash: str | None = None,
    ) -> None:
        if len(token_hashes) < 2:
            raise ValueError("At least two separately authenticated profiles required")
        digests = tuple(token_hashes.values())
        if len(set(digests)) != len(digests):
            raise ValueError("Each child profile must have a distinct token")
        if any(re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None for digest in digests):
            raise ValueError("Token values must be SHA-256 hex digests, never raw secrets")
        if any(re.fullmatch(r"[a-z][a-z0-9_-]{1,40}", owner) is None for owner in token_hashes):
            raise ValueError("Invalid family profile identifier")
        if not allowed_origins or any(
            not self._valid_origin(origin) for origin in allowed_origins
        ):
            raise ValueError("Explicit HTTPS (or loopback dev) origins are required")

        if parent_unlock_hash is not None and re.fullmatch(
            r"[0-9a-fA-F]{64}", parent_unlock_hash
        ) is None:
            raise ValueError("Parent unlock must be a server-held SHA-256 hex digest")
        self.repository = repository
        self.reader = CharacterBridgeReader(repository)
        self.token_hashes = dict(token_hashes)
        self.allowed_origins = frozenset(allowed_origins)
        self.parent_unlock_hash = (
            parent_unlock_hash.lower() if parent_unlock_hash else None
        )
        self._session_lock = threading.RLock()
        # Only token SHA-256 digests are retained on the server, not raw tokens.
        self._sessions: dict[str, tuple[str, float]] = {}
        self._parent_failures: list[float] = []

    @staticmethod
    def _valid_origin(origin: str) -> bool:
        parts = urlsplit(origin)
        return bool(
            parts.hostname
            and not parts.username
            and not parts.password
            and not parts.path
            and not parts.query
            and not parts.fragment
            and (parts.scheme == "https" or (
                parts.scheme == "http"
                and parts.hostname in {"127.0.0.1", "localhost", "::1"}
            ))
        )

    def authenticate(self, authorization: str) -> str | None:
        prefix = "Bearer "
        if not authorization.startswith(prefix):
            return None
        secret = authorization[len(prefix):]
        if not secret or len(secret) > 512:
            return None
        calculated = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        match: str | None = None
        for profile, digest in self.token_hashes.items():
            if hmac.compare_digest(calculated, digest.lower()):
                match = profile
        if match is not None:
            return match
        now = time.monotonic()
        with self._session_lock:
            record = self._sessions.get(calculated)
            if record is None:
                return None
            owner, expires_at = record
            if expires_at <= now:
                del self._sessions[calculated]
                return None
            return owner

    def _issue_child_session(self, authorization: str, body: bytes) -> BridgeResponse:
        if self.parent_unlock_hash is None:
            return BridgeResponse(
                HTTPStatus.SERVICE_UNAVAILABLE, {"error": "parent_login_not_configured"}
            )
        now = time.monotonic()
        with self._session_lock:
            self._parent_failures = [
                value for value in self._parent_failures
                if now - value < PARENT_FAILURE_WINDOW_SECONDS
            ]
            if len(self._parent_failures) >= PARENT_FAILURE_LIMIT:
                return BridgeResponse(
                    HTTPStatus.TOO_MANY_REQUESTS, {"error": "parent_login_rate_limited"}
                )

        prefix = "Bearer "
        secret = authorization[len(prefix):] if authorization.startswith(prefix) else ""
        digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        # The parent secret is used only for this exchange and never becomes
        # a child API token or part of the returned session.
        if not secret or len(secret) > 512 or not hmac.compare_digest(
            digest, self.parent_unlock_hash
        ):
            with self._session_lock:
                self._parent_failures.append(now)
            return BridgeResponse(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})

        try:
            requested = json.loads(body)
        except (UnicodeError, ValueError):
            return BridgeResponse(
                HTTPStatus.BAD_REQUEST, {"error": "invalid_profile_selection"}
            )
        if (
            not isinstance(requested, dict)
            or set(requested) != {"profile_id"}
            or not isinstance(requested["profile_id"], str)
            or requested["profile_id"] not in self.token_hashes
        ):
            return BridgeResponse(
                HTTPStatus.BAD_REQUEST, {"error": "invalid_profile_selection"}
            )

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._session_lock:
            self._sessions = {
                key: item for key, item in self._sessions.items()
                if item[1] > now
            }
            # Bounded session table even if a parent repeatedly signs in.
            if len(self._sessions) >= 32:
                oldest = min(self._sessions, key=lambda key: self._sessions[key][1])
                del self._sessions[oldest]
            self._sessions[token_hash] = (
                requested["profile_id"], now + SESSION_TTL_SECONDS
            )

        return BridgeResponse(HTTPStatus.CREATED, {
            "schema_version": "1.0",
            "access_token": token,
            "token_type": "Bearer",
            "expires_in_seconds": SESSION_TTL_SECONDS,
            "profile_id": requested["profile_id"],
        })

    def _revoke_child_session(self, authorization: str) -> BridgeResponse:
        if self.authenticate(authorization) is None:
            return BridgeResponse(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        secret = authorization[len("Bearer "):]
        digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        with self._session_lock:
            if digest not in self._sessions:
                return BridgeResponse(
                    HTTPStatus.FORBIDDEN, {"error": "only_ephemeral_sessions_revocable"}
                )
            del self._sessions[digest]
        return BridgeResponse(HTTPStatus.NO_CONTENT, {})

    def handle(
        self,
        *,
        method: str,
        path: str,
        authorization: str = "",
        origin: str | None = None,
        body: bytes = b"",
    ) -> BridgeResponse:
        if origin is not None and origin not in self.allowed_origins:
            return BridgeResponse(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})

        if method == "OPTIONS":
            return BridgeResponse(HTTPStatus.NO_CONTENT, {})

        route = urlsplit(path).path
        if route == "/family/sessions":
            if method != "POST":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            return self._issue_child_session(authorization, body)
        if route == "/family/sessions/current" and method == "DELETE":
            return self._revoke_child_session(authorization)

        owner = self.authenticate(authorization)
        if owner is None:
            return BridgeResponse(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})

        route = urlsplit(path).path
        if route == "/characters":
            if method == "GET":
                results = []
                for asset in self.repository.list_assets(AssetType.CHARACTER):
                    if asset.metadata.get("family_owner") != owner:
                        continue
                    if asset.status == ReviewStatus.ARCHIVED:
                        continue
                    results.append(self.reader._contract(asset).model_dump(mode="json"))
                return BridgeResponse(HTTPStatus.OK, {
                    "schema_version": "1.0", "characters": results,
                })
            if method == "POST":
                try:
                    requested = FamilyCharacterCreate.model_validate(json.loads(body))
                except (ValueError, UnicodeError, ValidationError):
                    return BridgeResponse(HTTPStatus.BAD_REQUEST, {
                        "error": "invalid_character_create",
                    })
                asset = Asset.create(
                    AssetType.CHARACTER,
                    display_name=requested.display_name,
                    slug=slugify(requested.display_name),
                    metadata={
                        "family_owner": owner,
                        "character_profile": requested.profile.model_dump(mode="json"),
                    },
                )
                asset.description = requested.description
                self.repository.save_asset(asset)
                return BridgeResponse(
                    HTTPStatus.CREATED,
                    self.reader._contract(asset).model_dump(mode="json"),
                )
            return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})

        parts = route.strip("/").split("/")
        if (
            len(parts) in (3, 4)
            and parts[0] == "characters"
            and parts[2] == "equipment"
        ):
            character_id = unquote(parts[1])
            if not character_id or "/" in character_id:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            asset = self.repository.get_asset(character_id)
            if (
                asset is None
                or asset.asset_type != AssetType.CHARACTER
                or asset.metadata.get("family_owner") != owner
            ):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})

            # Family inventories are separate canonical CreatorCollections.
            # Do not expose the desktop's shared COLL_DEFAULT to children.
            gateway = EquipmentBridgeGateway(
                self.repository,
                collection_id="COLL_FAMILY_" + owner,
                owner_key=owner,
            )
            if len(parts) == 3:
                if method != "GET":
                    return BridgeResponse(
                        HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                    )
                return BridgeResponse(HTTPStatus.OK, gateway.get_state(character_id))

            if method != "PUT":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            slot = unquote(parts[3])
            if not slot or "/" in slot:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            try:
                data = json.loads(body)
                if (
                    not isinstance(data, dict)
                    or set(data) != {"item_instance_id"}
                    or (
                        data["item_instance_id"] is not None
                        and not isinstance(data["item_instance_id"], str)
                    )
                ):
                    raise ValueError("item_instance_id required")
                state = gateway.set_slot(character_id, slot, data["item_instance_id"])
            except (ValueError, UnicodeError):
                return BridgeResponse(HTTPStatus.BAD_REQUEST, {
                    "error": "invalid_equipment_update",
                })
            return BridgeResponse(HTTPStatus.OK, state)

        if route.startswith("/characters/"):
            character_id = unquote(route[len("/characters/"):])
            if not character_id or "/" in character_id:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            asset = self.repository.get_asset(character_id)
            # Do not reveal whether another child's character exists.
            if (
                asset is None
                or asset.asset_type != AssetType.CHARACTER
                or asset.metadata.get("family_owner") != owner
            ):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            if method == "GET":
                return BridgeResponse(HTTPStatus.OK, self.reader.get_character(character_id))
            if method == "PUT":
                try:
                    payload = json.loads(body)
                    if not isinstance(payload, dict):
                        raise ValueError("Object body required")
                    result = self.reader.update_character(character_id, payload)
                except (ValueError, UnicodeError, CharacterWriteValidationError):
                    return BridgeResponse(HTTPStatus.BAD_REQUEST, {
                        "error": "invalid_character_update",
                    })
                except CharacterRevisionConflict as exc:
                    return BridgeResponse(HTTPStatus.CONFLICT, {
                        "error": "revision_conflict", "current_revision": exc.current_revision,
                    })
                return BridgeResponse(HTTPStatus.OK, result)
            return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})

        return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def build_family_server(
    application: FamilyApplication, *, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    """Dev HTTP binds loopback only; production requires a TLS reverse proxy."""

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Direct internet exposure is forbidden; use TLS reverse proxy")

    class Handler(BaseHTTPRequestHandler):
        server_version = "MiniUtopiaFamily"
        sys_version = ""

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._respond("OPTIONS")

        def do_GET(self) -> None:  # noqa: N802
            self._respond("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._respond("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._respond("PUT")

        def do_DELETE(self) -> None:  # noqa: N802
            self._respond("DELETE")

        def _respond(self, method: str) -> None:
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = -1
            if size < 0 or size > MAX_REQUEST_BODY_BYTES:
                response = BridgeResponse(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
                    "error": "request_too_large",
                })
            else:
                body = self.rfile.read(size) if size else b""
                try:
                    response = application.handle(
                        method=method,
                        path=self.path,
                        authorization=self.headers.get("Authorization", ""),
                        origin=self.headers.get("Origin"),
                        body=body,
                    )
                except Exception:
                    # Do not leak exception details or private data over HTTP.
                    response = BridgeResponse(HTTPStatus.SERVICE_UNAVAILABLE, {
                        "error": "service_unavailable",
                    })

            payload = json.dumps(response.payload, ensure_ascii=False).encode("utf-8")
            self.send_response(int(response.status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Vary", "Origin")
            origin = self.headers.get("Origin")
            if origin in application.allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.end_headers()
            if method != "OPTIONS":
                self.wfile.write(payload)

        def log_message(self, fmt: str, *args: object) -> None:
            # Suppress paths/tokens from access logs on shared systems.
            return

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Private Mini Utopia family API (loopback)")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    from studio.core.config import get_settings
    from studio.services.bootstrap import build_context

    origins = tuple(
        origin.strip() for origin in os.environ.get("FAMILY_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )
    # These are only SHA-256 hashes of separately generated long-lived
    # random tokens; original tokens must never be committed or logged.
    hashes = {
        name: digest
        for name, digest in (
            ("child_a", os.environ.get("FAMILY_CHILD_A_TOKEN_SHA256", "")),
            ("child_b", os.environ.get("FAMILY_CHILD_B_TOKEN_SHA256", "")),
        )
    }
    app = FamilyApplication(
        build_context(get_settings()).repository,
        token_hashes=hashes,
        allowed_origins=origins,
        parent_unlock_hash=os.environ.get("FAMILY_PARENT_UNLOCK_SHA256") or None,
    )
    server = build_family_server(app, port=args.port)
    print("Private family API listening on loopback; TLS proxy required for Web")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
