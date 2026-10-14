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
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal, Mapping
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from studio.bridge.characters import CharacterBridgeReader
from studio.bridge.equipment import EquipmentBridgeGateway
from studio.family_props import FamilyCraftedProp, craft_family_prop
from studio.family_films import FamilyFilmDraft, cast_is_owned, film_contract, save_film_draft
from studio.family_film_render import build_family_film_render_source
from studio.family_movie_review import current_review_state, decide_private_film_review
from studio.family_movie_media import (
    PrivateMovieMediaError, release_status, set_parent_release,
    download_released_media,
)
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
CAST_GRANT_TTL_SECONDS = 900
CAST_GRANT_LIMIT = 16


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
        private_movie_root: Path | None = None,
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
        self.private_movie_root = (
            Path(private_movie_root) if private_movie_root is not None else None
        )
        self._session_lock = threading.RLock()
        # Only token SHA-256 digests are retained on the server, not raw tokens.
        self._sessions: dict[str, tuple[str, float]] = {}
        self._parent_failures: list[float] = []
        self._cast_grants: dict[str, tuple[str, str, str, float]] = {}

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

    def _require_parent(self, authorization: str) -> BridgeResponse | None:
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

        return None

    def _issue_child_session(self, authorization: str, body: bytes) -> BridgeResponse:
        denied = self._require_parent(authorization)
        if denied is not None:
            return denied

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
        now = time.monotonic()
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

    def _issue_cast_grant(self, authorization: str, body: bytes) -> BridgeResponse:
        denied = self._require_parent(authorization)
        if denied is not None:
            return denied
        try:
            data = json.loads(body)
        except (UnicodeError, ValueError):
            return BridgeResponse(HTTPStatus.BAD_REQUEST, {"error": "invalid_cast_grant"})
        expected = {"viewer_profile_id", "source_profile_id", "character_id"}
        if not isinstance(data, dict) or set(data) != expected or any(
            not isinstance(value, str) for value in data.values()
        ):
            return BridgeResponse(HTTPStatus.BAD_REQUEST, {"error": "invalid_cast_grant"})
        viewer = data["viewer_profile_id"]
        source = data["source_profile_id"]
        cid = data["character_id"]
        if (
            viewer not in self.token_hashes
            or source not in self.token_hashes
            or viewer == source
            or not re.fullmatch(r"CHAR_[A-Za-z0-9_-]{3,96}", cid)
        ):
            return BridgeResponse(HTTPStatus.BAD_REQUEST, {"error": "invalid_cast_grant"})
        asset = self.repository.get_asset(cid)
        if (
            asset is None
            or asset.asset_type != AssetType.CHARACTER
            or asset.status == ReviewStatus.ARCHIVED
            or asset.metadata.get("family_owner") != source
        ):
            return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        now = time.monotonic()
        grant_id = "CAST_" + secrets.token_urlsafe(24)
        with self._session_lock:
            self._cast_grants = {
                key: entry for key, entry in self._cast_grants.items()
                if entry[3] > now
            }
            if len(self._cast_grants) >= CAST_GRANT_LIMIT:
                oldest = min(self._cast_grants, key=lambda key: self._cast_grants[key][3])
                del self._cast_grants[oldest]
            self._cast_grants[grant_id] = (
                viewer, source, cid, now + CAST_GRANT_TTL_SECONDS
            )
        return BridgeResponse(HTTPStatus.CREATED, {
            "schema_version": "1.0", "grant_id": grant_id,
            "viewer_profile_id": viewer, "source_profile_id": source,
            "character_id": cid, "expires_in_seconds": CAST_GRANT_TTL_SECONDS,
        })

    def _revoke_cast_grant(self, authorization: str, grant_id: str) -> BridgeResponse:
        denied = self._require_parent(authorization)
        if denied is not None:
            return denied
        with self._session_lock:
            if self._cast_grants.pop(grant_id, None) is None:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        return BridgeResponse(HTTPStatus.NO_CONTENT, {})

    def _list_cast_guests(self, viewer: str) -> BridgeResponse:
        now = time.monotonic()
        with self._session_lock:
            matches = [
                (grant_id, source, cid, expires)
                for grant_id, (owner, source, cid, expires) in self._cast_grants.items()
                if owner == viewer and expires > now
            ]
        guests = []
        for grant_id, source, cid, expires in matches:
            asset = self.repository.get_asset(cid)
            if (
                asset is None
                or asset.asset_type != AssetType.CHARACTER
                or asset.status == ReviewStatus.ARCHIVED
                or asset.metadata.get("family_owner") != source
            ):
                continue
            guests.append({
                "grant_id": grant_id, "character_id": cid,
                "display_name": asset.display_name,
                "expires_in_seconds": max(0, int(expires - now)),
            })
        return BridgeResponse(HTTPStatus.OK, {
            "schema_version": "1.0", "guests": guests,
        })

    def _get_cast_guest(self, viewer: str, grant_id: str) -> BridgeResponse:
        now = time.monotonic()
        with self._session_lock:
            grant = self._cast_grants.get(grant_id)
            if grant is None or grant[0] != viewer or grant[3] <= now:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            _, source, cid, _expires = grant
        asset = self.repository.get_asset(cid)
        if (
            asset is None
            or asset.asset_type != AssetType.CHARACTER
            or asset.status == ReviewStatus.ARCHIVED
            or asset.metadata.get("family_owner") != source
        ):
            return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        contract = self.reader._contract(asset).model_dump(mode="json")
        # Grant covers acting appearance + equipped items, not biography,
        # revisions, private notes, or the sibling's full wardrobe inventory.
        limited = {
            "schema_version": "1.0",
            "character_id": cid,
            "display_name": contract["display_name"],
            "profile": {"avatar": contract["profile"]["avatar"]},
        }
        gateway = EquipmentBridgeGateway(
            self.repository,
            collection_id="COLL_FAMILY_" + source,
            owner_key=source,
        )
        runtime = gateway.get_state(cid)["runtime"]
        return BridgeResponse(HTTPStatus.OK, {
            "schema_version": "1.0", "grant_id": grant_id,
            "character": limited, "equipment_runtime": runtime,
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

    def private_mp4_for_download(
        self, *, authorization: str, film_id: str, origin: str | None
    ) -> bytes | None:
        # The binary handler does not pass raw tokens into a URL, redirect,
        # static file_server or browser cache; it requires a child bearer.
        if origin is not None and origin not in self.allowed_origins:
            return None
        if not re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", film_id):
            return None
        owner = self.authenticate(authorization)
        if owner is None:
            return None
        with self._session_lock:
            return download_released_media(
                self.repository, self.private_movie_root,
                owner=owner, film_id=film_id,
            )

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
        if route == "/family/film-reviews":
            if method != "POST":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            denied = self._require_parent(authorization)
            if denied is not None:
                return denied
            try:
                data = json.loads(body)
            except (UnicodeError, ValueError):
                return BridgeResponse(
                    HTTPStatus.BAD_REQUEST, {"error": "invalid_film_review"}
                )
            if (
                not isinstance(data, dict)
                or set(data) != {"profile_id", "film_id", "revision", "decision"}
                or any(not isinstance(value, str) for value in data.values())
                or data["profile_id"] not in self.token_hashes
                or not re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", data["film_id"])
                or not re.fullmatch(r"[0-9]{1,12}", data["revision"])
                or data["decision"] not in ("approve", "revoke")
            ):
                return BridgeResponse(
                    HTTPStatus.BAD_REQUEST, {"error": "invalid_film_review"}
                )
            with self._session_lock:
                try:
                    review = decide_private_film_review(
                        self.repository,
                        owner=data["profile_id"], film_id=data["film_id"],
                        revision=data["revision"], decision=data["decision"],
                    )
                except ValueError:
                    return BridgeResponse(
                        HTTPStatus.CONFLICT, {"error": "revision_conflict"}
                    )
            if review is None:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return BridgeResponse(HTTPStatus.OK, review)
        if route == "/family/movie-releases":
            if method != "POST":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            denied = self._require_parent(authorization)
            if denied is not None:
                return denied
            try:
                data = json.loads(body)
            except (UnicodeError, ValueError):
                return BridgeResponse(
                    HTTPStatus.BAD_REQUEST, {"error": "invalid_movie_release"}
                )
            if (
                not isinstance(data, dict)
                or set(data) != {"profile_id", "film_id", "revision", "decision"}
                or any(not isinstance(value, str) for value in data.values())
                or data["profile_id"] not in self.token_hashes
                or not re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", data["film_id"])
                or not re.fullmatch(r"[0-9]{1,12}", data["revision"])
                or data["decision"] not in ("release", "revoke")
            ):
                return BridgeResponse(
                    HTTPStatus.BAD_REQUEST, {"error": "invalid_movie_release"}
                )
            with self._session_lock:
                try:
                    release = set_parent_release(
                        self.repository, self.private_movie_root,
                        owner=data["profile_id"], film_id=data["film_id"],
                        revision=data["revision"], decision=data["decision"],
                    )
                except PrivateMovieMediaError:
                    return BridgeResponse(
                        HTTPStatus.CONFLICT, {"error": "private_movie_not_ready"}
                    )
                except ValueError:
                    return BridgeResponse(
                        HTTPStatus.CONFLICT, {"error": "revision_conflict"}
                    )
            if release is None:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return BridgeResponse(HTTPStatus.OK, release)

        if route == "/family/cast-grants":
            if method != "POST":
                return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
            return self._issue_cast_grant(authorization, body)
        if route.startswith("/family/cast-grants/"):
            if method != "DELETE":
                return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
            grant_id = unquote(route[len("/family/cast-grants/"):])
            if not re.fullmatch(r"CAST_[A-Za-z0-9_-]{20,64}", grant_id):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return self._revoke_cast_grant(authorization, grant_id)

        owner = self.authenticate(authorization)
        if owner is None:
            return BridgeResponse(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})

        route = urlsplit(path).path
        if route == "/family/films":
            if method == "GET":
                films = [
                    film_contract(asset)
                    for asset in self.repository.list_assets(AssetType.FILM)
                    if asset.metadata.get("family_owner") == owner
                    and asset.status != ReviewStatus.ARCHIVED
                    and "family_film_draft" in asset.metadata
                ]
                return BridgeResponse(HTTPStatus.OK, {
                    "schema_version": "1.0", "films": films,
                })
            if method != "POST":
                return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {
                    "error": "method_not_allowed",
                })
            try:
                draft = FamilyFilmDraft.model_validate(json.loads(body))
            except (ValueError, UnicodeError, ValidationError):
                return BridgeResponse(HTTPStatus.BAD_REQUEST, {
                    "error": "invalid_film_draft",
                })
            if not cast_is_owned(self.repository, owner, draft):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            with self._session_lock:
                count = sum(
                    1 for asset in self.repository.list_assets(AssetType.FILM)
                    if asset.metadata.get("family_owner") == owner
                )
                if count >= 20:
                    return BridgeResponse(HTTPStatus.CONFLICT, {
                        "error": "film_draft_limit",
                    })
                saved = save_film_draft(self.repository, owner, draft)
            return BridgeResponse(HTTPStatus.CREATED, saved)

        if route.endswith("/media-status") and route.startswith("/family/films/"):
            film_id = unquote(route[len("/family/films/"):-len("/media-status")])
            if not re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", film_id):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            if method != "GET":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            with self._session_lock:
                result = release_status(
                    self.repository, self.private_movie_root,
                    owner=owner, film_id=film_id,
                )
            if result is None:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return BridgeResponse(HTTPStatus.OK, result)

        if route.endswith("/review") and route.startswith("/family/films/"):
            film_id = unquote(route[len("/family/films/"):-len("/review")])
            if not re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", film_id):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            if method != "GET":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            with self._session_lock:
                review = current_review_state(
                    self.repository, owner=owner, film_id=film_id,
                )
            if review is None:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return BridgeResponse(HTTPStatus.OK, review)

        if route.endswith("/render-source") and route.startswith("/family/films/"):
            film_id = unquote(
                route[len("/family/films/"):-len("/render-source")]
            )
            if not re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", film_id):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            if method != "GET":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            # No arbitrary contract upload: all Character and equipment data
            # originate in the current child's canonical SQLite collection.
            source = build_family_film_render_source(
                self.repository, owner=owner, film_id=film_id
            )
            if source is None:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return BridgeResponse(HTTPStatus.OK, source)

        if route.startswith("/family/films/"):
            film_id = unquote(route[len("/family/films/"):])
            if not film_id.startswith("FILM_") or "/" in film_id:
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            with self._session_lock:
                asset = self.repository.get_asset(film_id)
                if (
                    asset is None or asset.asset_type != AssetType.FILM
                    or asset.status == ReviewStatus.ARCHIVED
                    or asset.metadata.get("family_owner") != owner
                    or "family_film_draft" not in asset.metadata
                ):
                    return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                if method == "GET":
                    return BridgeResponse(HTTPStatus.OK, film_contract(asset))
                if method != "PUT":
                    return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {
                        "error": "method_not_allowed",
                    })
                try:
                    data = json.loads(body)
                    if not isinstance(data, dict) or set(data) != {"revision", "draft"}:
                        raise ValueError("Expected revision and draft")
                    if not isinstance(data["revision"], str):
                        raise ValueError("Expected revision string")
                    draft = FamilyFilmDraft.model_validate(data["draft"])
                except (ValueError, UnicodeError, ValidationError):
                    return BridgeResponse(HTTPStatus.BAD_REQUEST, {
                        "error": "invalid_film_draft",
                    })
                if data["revision"] != str(asset.version):
                    return BridgeResponse(HTTPStatus.CONFLICT, {
                        "error": "revision_conflict", "current_revision": str(asset.version),
                    })
                if not cast_is_owned(self.repository, owner, draft):
                    return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return BridgeResponse(
                    HTTPStatus.OK, save_film_draft(self.repository, owner, draft, asset)
                )

        if route == "/family/cast-guests":
            if method != "GET":
                return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
            return self._list_cast_guests(owner)
        if route.startswith("/family/cast-guests/"):
            if method != "GET":
                return BridgeResponse(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
            grant_id = unquote(route[len("/family/cast-guests/"):])
            if not re.fullmatch(r"CAST_[A-Za-z0-9_-]{20,64}", grant_id):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return self._get_cast_guest(owner, grant_id)
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
        if len(parts) == 3 and parts[0] == "characters" and parts[2] == "crafted-props":
            character_id = unquote(parts[1])
            asset = self.repository.get_asset(character_id)
            if (
                not character_id.startswith("CHAR_")
                or "/" in character_id
                or asset is None
                or asset.asset_type != AssetType.CHARACTER
                or asset.status == ReviewStatus.ARCHIVED
                or asset.metadata.get("family_owner") != owner
            ):
                return BridgeResponse(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            if method != "POST":
                return BridgeResponse(
                    HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}
                )
            try:
                request = FamilyCraftedProp.model_validate(json.loads(body))
                crafted = craft_family_prop(
                    self.repository, owner=owner,
                    character_id=character_id, request=request,
                )
            except (ValueError, UnicodeError, ValidationError):
                return BridgeResponse(
                    HTTPStatus.BAD_REQUEST, {"error": "invalid_crafted_prop"}
                )
            gateway = EquipmentBridgeGateway(
                self.repository,
                collection_id="COLL_FAMILY_" + owner, owner_key=owner,
            )
            return BridgeResponse(HTTPStatus.CREATED, {
                "schema_version": "1.0",
                "crafted": crafted,
                "equipment": gateway.get_state(character_id),
            })

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

            # Authenticated binary delivery bypasses Caddy's static file
            # server. No bearer in URLs, cookies, redirects or shared caches.
            if method == "GET":
                download_route = re.fullmatch(
                    r"/family/films/(FILM_[A-Za-z0-9_-]{3,96})/download",
                    urlsplit(self.path).path,
                )
                if download_route is not None:
                    binary = application.private_mp4_for_download(
                        authorization=self.headers.get("Authorization", ""),
                        origin=self.headers.get("Origin"),
                        film_id=download_route.group(1),
                    )
                    if binary is not None:
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-Type", "video/mp4")
                        self.send_header("Content-Length", str(len(binary)))
                        self.send_header(
                            "Content-Disposition",
                            'attachment; filename="mini-utopia-'
                            + download_route.group(1) + '.mp4"',
                        )
                        self.send_header("Cache-Control", "private, no-store")
                        self.send_header("X-Content-Type-Options", "nosniff")
                        self.send_header("Referrer-Policy", "no-referrer")
                        self.send_header("Vary", "Origin")
                        origin = self.headers.get("Origin")
                        if origin in application.allowed_origins:
                            self.send_header("Access-Control-Allow-Origin", origin)
                        self.end_headers()
                        self.wfile.write(binary)
                        return
                    response = BridgeResponse(
                        HTTPStatus.NOT_FOUND, {"error": "not_found"}
                    )

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

    from pathlib import Path
    from studio.repositories.sqlite import SQLiteStudioRepository

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
    # The private family API needs only the canonical SQLite repository,
    # not the Streamlit UI, AI providers, or production studio plugins.
    database_path = Path(os.environ.get("DATABASE_PATH", "data/studio.db"))
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    app = FamilyApplication(
        SQLiteStudioRepository(database_path),
        token_hashes=hashes,
        allowed_origins=origins,
        parent_unlock_hash=os.environ.get("FAMILY_PARENT_UNLOCK_SHA256") or None,
        private_movie_root=(
            Path(os.environ["FAMILY_PRIVATE_MOVIES_ROOT"])
            if os.environ.get("FAMILY_PRIVATE_MOVIES_ROOT") else None
        ),
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
