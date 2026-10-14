"""Read-only family backup/restore audit; never export household data to CI.

SQLite online backup runs into a 0700 temporary folder, the restored copy is
reopened and checked for integrity and owner-scoped assets. Neither private
drafts nor saved MP4 bytes are logged, printed or uploaded anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from studio.core.enums import AssetType
from studio.family_movie_media import release_status, PrivateMovieMediaError
from studio.repositories.sqlite import SQLiteStudioRepository


class FamilyBackupAuditError(RuntimeError):
    """Safe failure message; never contains a child's notes or media content."""


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    # Fixed allowlist: never interpolate caller-provided identifiers.
    if table not in {
        "assets", "collections", "jobs", "stories", "episodes", "quests"
    }:
        raise FamilyBackupAuditError("Unsupported private backup table")
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def audit_private_family_backup(
    db_path: Path, *, media_root: Path | None = None,
) -> dict:
    path = Path(db_path).resolve()
    if not path.is_file() or Path(db_path).is_symlink():
        raise FamilyBackupAuditError("Private SQLite database missing or unsafe")
    # No inplace backup/restore and never write a live family database.
    try:
        with tempfile.TemporaryDirectory(
            prefix="mini-utopia-private-restore-audit-"
        ) as scratch:
            folder = Path(scratch)
            folder.chmod(0o700)
            restored = folder / "restored-for-audit.sqlite3"
            # SQLite online backup is transactionally consistent, even if a
            # short-lived child save completes during the audit.
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as live:
                with sqlite3.connect(restored) as snapshot:
                    live.backup(snapshot, pages=128, sleep=0.05)
            restored.chmod(0o600)
            with sqlite3.connect(
                restored.as_uri() + "?mode=ro", uri=True
            ) as validation:
                rows = validation.execute("PRAGMA integrity_check").fetchall()
                if rows != [("ok",)]:
                    raise FamilyBackupAuditError("Restored SQLite integrity check failed")
                if validation.execute("PRAGMA foreign_key_check").fetchall():
                    raise FamilyBackupAuditError("Restored SQLite foreign key check failed")
                counts = {
                    table: _table_count(validation, table)
                    for table in ("assets", "collections", "jobs", "stories", "episodes", "quests")
                }

            # Reopen the actual restored SQLite schema via the canonical Core
            # repository, not only sqlite3 raw queries.
            repo = SQLiteStudioRepository(restored)
            films = repo.list_assets(AssetType.FILM)
            owners = {"child_a": 0, "child_b": 0}
            invalid_owner = 0
            released = 0
            stale_receipts = 0
            for film in films:
                owner = film.metadata.get("family_owner")
                if owner not in owners:
                    invalid_owner += 1
                    continue
                owners[owner] += 1
                if media_root is not None:
                    try:
                        state = release_status(
                            repo, Path(media_root), owner=owner,
                            film_id=film.asset_id,
                        )
                    except (OSError, PrivateMovieMediaError):
                        raise FamilyBackupAuditError(
                            "Private media directory is missing or unsafe"
                        ) from None
                    if state and state["released_to_child"]:
                        released += 1
                    elif film.metadata.get("family_movie_release", {}).get(
                        "decision"
                    ) == "release":
                        # Stale/inaccessible receipts do not expose downloads;
                        # report only aggregate count for the adult to review.
                        stale_receipts += 1

            return {
                "schema_version": "1.0",
                "integrity": "ok",
                "restored_schema": "ok",
                "table_counts": counts,
                "private_film_count": owners,
                "unexpected_film_owner_count": invalid_owner,
                "verified_released_media_count": released,
                "stale_or_inaccessible_release_count": stale_receipts,
                "media_checked": media_root is not None,
                "original_database_modified": False,
                "temporary_copy_retained": False,
            }
    except (sqlite3.DatabaseError, OSError) as exc:
        raise FamilyBackupAuditError(
            "Private restore audit failed; verify SQLite and storage"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adult-only private SQLite restore and MP4 permission audit"
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--media-root", type=Path)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        parser.error("Never inspect real family backups on public GitHub CI")
    try:
        result = audit_private_family_backup(
            args.db, media_root=args.media_root
        )
    except FamilyBackupAuditError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
