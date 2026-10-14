"""Backup verification runs only on synthetic family data in public CI."""
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from studio.family_api import FamilyApplication
from studio.family_backup_audit import (
    FamilyBackupAuditError, audit_private_family_backup,
)
from studio.family_movie_media import approved_fingerprint, media_path
from studio.repositories.sqlite import SQLiteStudioRepository


def make_app(database, media):
    return FamilyApplication(
        SQLiteStudioRepository(database),
        token_hashes={
            "child_a": hashlib.sha256(b"synthetic-backup-child-a").hexdigest(),
            "child_b": hashlib.sha256(b"synthetic-backup-child-b").hexdigest(),
        },
        parent_unlock_hash=hashlib.sha256(
            b"synthetic_adult_backup_secret_0123456789abcdef"
        ).hexdigest(),
        allowed_origins=("https://family.example",),
        private_movie_root=media,
    )


def request(app, method, path, body=None, token="synthetic-backup-child-a"):
    return app.handle(
        method=method, path=path,
        authorization="Bearer " + token,
        origin="https://family.example",
        body=json.dumps(body).encode() if body is not None else b"",
    )


def test_private_backup_restores_canonical_films_and_verifies_released_video(tmp_path):
    database = tmp_path / "family.db"
    media = tmp_path / "private-media"
    media.mkdir(mode=0o700)
    app = make_app(database, media)
    actor = request(app, "POST", "/characters", {
        "display_name": "Synthetic Sheep",
        "description": "Private actor description must never be printed"
    })
    saved = request(app, "POST", "/family/films", {
        "schema_version": "1.0",
        "display_name": "Synthetic Cloud Story",
        "character_id": actor.payload["character_id"],
        "camera": "close", "action": "celebrate",
        "duration_seconds": 30,
        "private_story_note": "Never echo private child's story"
    })
    assert saved.status == 201
    film = saved.payload
    adult = "synthetic_adult_backup_secret_0123456789abcdef"
    approval = {
        "profile_id": "child_a", "film_id": film["film_id"],
        "revision": film["revision"], "decision": "approve"
    }
    assert request(app, "POST", "/family/film-reviews",
                   approval, token=adult).status == 200
    fp = approved_fingerprint(
        app.repository, owner="child_a", film_id=film["film_id"]
    )
    file = media_path(
        media, owner="child_a", film_id=film["film_id"],
        fingerprint=fp, create_dirs=True
    )
    video = b"\x00\x00\x00\x18ftypisom" + b"x" * 800
    file.write_bytes(video)
    file.chmod(0o600)
    release = request(app, "POST", "/family/movie-releases",
                      {**approval, "decision": "release"}, token=adult)
    assert release.status == 200
    db_bytes_before = database.read_bytes()

    result = audit_private_family_backup(database, media_root=media)
    assert result["integrity"] == "ok"
    assert result["restored_schema"] == "ok"
    assert result["table_counts"]["assets"] >= 2
    assert result["private_film_count"]["child_a"] == 1
    assert result["private_film_count"]["child_b"] == 0
    assert result["verified_released_media_count"] == 1
    assert result["stale_or_inaccessible_release_count"] == 0
    assert result["original_database_modified"] is False
    assert result["temporary_copy_retained"] is False
    assert database.read_bytes() == db_bytes_before
    assert "Never echo" not in json.dumps(result)
    assert "description" not in json.dumps(result)
    assert "synthetic_adult_backup_secret" not in json.dumps(result)

    # Real footage is still never exposed in the backup verification result.
    file.write_bytes(video + b"unauthorized modification")
    changed = audit_private_family_backup(database, media_root=media)
    assert changed["verified_released_media_count"] == 0
    assert changed["stale_or_inaccessible_release_count"] == 1

    no_media = audit_private_family_backup(database)
    assert no_media["media_checked"] is False
    assert no_media["table_counts"] == result["table_counts"]


def test_missing_corrupt_and_symlinked_live_backup_sources_fail_closed(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FamilyBackupAuditError, match="missing"):
        audit_private_family_backup(missing)

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not really SQLite")
    with pytest.raises(FamilyBackupAuditError, match="failed"):
        audit_private_family_backup(corrupt)

    real = tmp_path / "real.db"
    sqlite3.connect(real).close()
    shortcut = tmp_path / "shortcut.db"
    shortcut.symlink_to(real)
    with pytest.raises(FamilyBackupAuditError, match="unsafe"):
        audit_private_family_backup(shortcut)
