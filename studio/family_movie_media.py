"""Private, parent-released film files; never served as static Web assets.

Each MP4 is named after the SHA256 of the parent-reviewed render inputs and
lives in a private owner/film directory outside Git. A *second*, explicit
parent decision releases the actual encoded bytes to the child who owns it.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path

from studio.core.enums import AssetType, ReviewStatus
from studio.family_movie_review import current_review_state
from studio.models.asset import now_utc
from studio.repositories.base import StudioRepository

MAX_PRIVATE_MP4_BYTES = 32 * 1024 * 1024
FILM_ID_RE = re.compile(r"FILM_[A-Za-z0-9_-]{3,96}\Z")
SHA_RE = re.compile(r"[a-f0-9]{64}\Z")


class PrivateMovieMediaError(ValueError):
    pass


def approved_fingerprint(
    repository: StudioRepository, owner: str, film_id: str
) -> str | None:
    state = current_review_state(
        repository, owner=owner, film_id=film_id
    )
    if state is None or not state["approved_for_private_render"]:
        return None
    asset = repository.get_asset(film_id)
    value = asset.metadata.get("family_movie_review", {}).get("fingerprint", "")
    if isinstance(value, str) and SHA_RE.fullmatch(value):
        return value
    return None


def _private_folder(path: Path, create: bool = False) -> Path:
    if path.is_symlink():
        raise PrivateMovieMediaError("Symlinked private directory forbidden")
    if create and not path.exists():
        path.mkdir(mode=0o700)
    if not path.is_dir():
        raise PrivateMovieMediaError("Private movie directory is missing")
    st = path.stat()
    if (
        not stat.S_ISDIR(st.st_mode)
        or (os.name == "posix" and (
            st.st_uid != os.getuid() or (st.st_mode & 0o077)
        ))
    ):
        raise PrivateMovieMediaError("Private directory requires owner-only access")
    return path


def media_path(
    root: Path, *, owner: str, film_id: str, fingerprint: str,
    create_dirs: bool = False,
) -> Path:
    if owner not in ("child_a", "child_b"):
        raise PrivateMovieMediaError("Invalid movie owner")
    if not FILM_ID_RE.fullmatch(film_id) or not SHA_RE.fullmatch(fingerprint):
        raise PrivateMovieMediaError("Invalid private media address")
    root = Path(root)
    if not root.is_absolute():
        raise PrivateMovieMediaError("Media root must be absolute")
    _private_folder(root)
    owner_dir = _private_folder(root / owner, create_dirs)
    film_dir = _private_folder(owner_dir / film_id, create_dirs)
    target = film_dir / (fingerprint + ".mp4")
    if target.is_symlink():
        raise PrivateMovieMediaError("Symlinked private MP4 forbidden")
    return target


def read_private_media(path: Path) -> tuple[bytes, str] | None:
    """Read one bounded, owner-only regular file without following symlinks."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except (OSError, ValueError):
        return None
    try:
        st = os.fstat(fd)
        if (
            not stat.S_ISREG(st.st_mode)
            or not 256 < st.st_size <= MAX_PRIVATE_MP4_BYTES
            or (os.name == "posix" and (
                st.st_uid != os.getuid() or st.st_mode & 0o077
            ))
        ):
            return None
        with os.fdopen(fd, "rb", closefd=False) as source:
            blob = source.read(MAX_PRIVATE_MP4_BYTES + 1)
        if len(blob) != st.st_size or blob[4:8] != b"ftyp":
            return None
        return blob, hashlib.sha256(blob).hexdigest()
    finally:
        os.close(fd)


def _film(repository: StudioRepository, owner: str, film_id: str):
    asset = repository.get_asset(film_id)
    if (
        asset is None or asset.asset_type != AssetType.FILM
        or asset.status == ReviewStatus.ARCHIVED
        or asset.metadata.get("family_owner") != owner
    ):
        return None
    return asset


def release_status(
    repository: StudioRepository, root: Path | None,
    *, owner: str, film_id: str,
) -> dict | None:
    asset = _film(repository, owner, film_id)
    if asset is None:
        return None
    fp = approved_fingerprint(repository, owner, film_id)
    receipt = asset.metadata.get("family_movie_release", {})
    released = False
    size = 0
    if (
        fp is not None and root is not None
        and isinstance(receipt, dict)
        and receipt.get("decision") == "release"
        and receipt.get("revision") == str(asset.version)
        and receipt.get("fingerprint") == fp
        and SHA_RE.fullmatch(str(receipt.get("media_sha256", "")))
    ):
        try:
            file = media_path(
                root, owner=owner, film_id=film_id, fingerprint=fp,
            )
            data = read_private_media(file)
            if data is not None and data[1] == receipt["media_sha256"]:
                released = True
                size = len(data[0])
        except PrivateMovieMediaError:
            pass
    return {
        "schema_version": "1.0",
        "film_id": film_id,
        "revision": str(asset.version),
        "released_to_child": released,
        "bytes": size,
    }


def set_parent_release(
    repository: StudioRepository, root: Path | None,
    *, owner: str, film_id: str, revision: str, decision: str,
) -> dict | None:
    """Parent caller verified separately by server authentication."""
    if decision not in ("release", "revoke"):
        raise ValueError("Invalid parent release decision")
    asset = _film(repository, owner, film_id)
    if asset is None:
        return None
    if revision != str(asset.version):
        raise ValueError("revision_conflict")
    fingerprint = approved_fingerprint(repository, owner, film_id)
    digest = ""
    if decision == "release":
        if fingerprint is None or root is None:
            raise PrivateMovieMediaError("Parent must approve current film first")
        path = media_path(
            root, owner=owner, film_id=film_id, fingerprint=fingerprint,
        )
        verified = read_private_media(path)
        if verified is None:
            raise PrivateMovieMediaError("Private MP4 is missing or unsafe")
        digest = verified[1]
    asset.metadata["family_movie_release"] = {
        "schema_version": "1.0", "decision": decision,
        "revision": revision, "fingerprint": fingerprint or "",
        "media_sha256": digest,
    }
    asset.updated_at = now_utc()
    repository.save_asset(asset)
    return release_status(repository, root, owner=owner, film_id=film_id)


def download_released_media(
    repository: StudioRepository, root: Path | None,
    *, owner: str, film_id: str,
) -> bytes | None:
    if root is None:
        return None
    asset = _film(repository, owner, film_id)
    if asset is None:
        return None
    fp = approved_fingerprint(repository, owner, film_id)
    if fp is None:
        return None
    receipt = asset.metadata.get("family_movie_release", {})
    if (
        not isinstance(receipt, dict)
        or receipt.get("decision") != "release"
        or receipt.get("revision") != str(asset.version)
        or receipt.get("fingerprint") != fp
    ):
        return None
    try:
        path = media_path(root, owner=owner, film_id=film_id, fingerprint=fp)
        verified = read_private_media(path)
    except PrivateMovieMediaError:
        return None
    if verified is None or verified[1] != receipt.get("media_sha256"):
        return None
    return verified[0]
