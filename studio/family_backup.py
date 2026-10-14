"""Consistent read-only SQLite backup for a private Mini Utopia family.

Usage:
  docker compose -f deploy/family/compose.yaml exec -T api \
      python -m studio.family_backup /data/studio.db > PRIVATE_BACKUP.sqlite

The caller is responsible for protected, off-host storage of stdout. Backups
must never be uploaded to the public GitHub repository or CI artifacts.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


def copy_sqlite_to_stdout(source: str | Path) -> None:
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError("Family database does not exist")

    fd, snapshot_path = tempfile.mkstemp(suffix=".sqlite", prefix="family-backup-")
    os.close(fd)
    try:
        # SQLite backup() takes a transactionally consistent snapshot even
        # while the live database receives new Character/Equipment writes.
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as src:
            with sqlite3.connect(snapshot_path) as dst:
                src.backup(dst)

        with open(snapshot_path, "rb") as snapshot:
            while part := snapshot.read(1024 * 256):
                sys.stdout.buffer.write(part)
        sys.stdout.buffer.flush()
    finally:
        try:
            os.unlink(snapshot_path)
        except FileNotFoundError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Private SQLite backup to stdout")
    parser.add_argument("database_path", type=Path)
    args = parser.parse_args()
    copy_sqlite_to_stdout(args.database_path)


if __name__ == "__main__":
    main()
