"""Private movie receipt helpers for version-bound local renders."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def receipt_path(movie: Path) -> Path:
    return Path(str(movie) + ".json")


def movie_digest(movie: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with movie.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > 64 * 1024 * 1024:
                raise ValueError("movie_too_large")
            digest.update(chunk)
    if size <= 256:
        raise ValueError("movie_empty")
    return digest.hexdigest(), size


def write_receipt(
    movie: Path, *, owner: str, film_id: str, revision: str,
    fingerprint: str,
) -> Path:
    """Create an exclusive receipt after successful private rendering."""
    import os
    import re

    if owner not in ("child_a", "child_b"):
        raise ValueError("invalid_owner")
    if re.fullmatch(r"FILM_[A-Za-z0-9_-]{3,96}", film_id) is None:
        raise ValueError("invalid_film_id")
    if re.fullmatch(r"[0-9]{1,12}", revision) is None:
        raise ValueError("invalid_revision")
    if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise ValueError("invalid_fingerprint")
    digest, size = movie_digest(movie)
    record = {
        "schema_version": "1.0", "owner": owner, "film_id": film_id,
        "revision": revision, "fingerprint": fingerprint,
        "sha256": digest, "bytes": size,
    }
    receipt = receipt_path(movie)
    with receipt.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
    receipt.chmod(0o600)
    return receipt
