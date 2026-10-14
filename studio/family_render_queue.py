"""Single-host, adult-operated private render queue stored in canonical SQLite.

There is intentionally NO public HTTP endpoint and no child token in this
module. A trusted adult enqueues an already-reviewed FILM; one private worker
claims exactly one job transactionally and invokes the isolated MP4 renderer.
A crash leaves the job blocked in 'running' until manual recovery (no
automatic re-run of expensive/private jobs).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Callable

from studio.family_movie_media import (
    PrivateMovieMediaError, approved_fingerprint, media_path, read_private_media,
)
from studio.family_private_movie_worker import PrivateMovieError, render_private_movie
from studio.repositories.sqlite import SQLiteStudioRepository


MAX_OUTSTANDING = 4
MAX_PER_CHILD_OUTSTANDING = 2
MAX_DAILY_SUBMISSIONS = 8
MAX_ATTEMPTS = 2
MIN_FREE_BYTES = 128 * 1024 * 1024

QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS private_family_render_queue (
    job_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    film_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    fps INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued','running','completed','failed','blocked')
    ),
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    error_code TEXT NOT NULL DEFAULT '',
    UNIQUE(owner, film_id, revision, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_private_family_render_queue_state
  ON private_family_render_queue(status, created_at);
"""


class PrivateRenderQueueError(ValueError):
    """Safe operational error; never include a child's scene or video bytes."""


class PrivateFamilyRenderQueue:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        if not self.db_path.is_file() or self.db_path.is_symlink():
            raise PrivateRenderQueueError("Private family database is missing or unsafe")
        with self._connect() as connection:
            connection.executescript(QUEUE_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        # Never include a child's profile, story note, image, or auth token.
        return {
            field: row[field] for field in (
                "job_id", "owner", "film_id", "revision", "fingerprint",
                "fps", "status", "attempts", "error_code",
            )
        }

    def _approved(self, owner: str, film_id: str) -> tuple[str, str] | None:
        if owner not in ("child_a", "child_b"):
            return None
        repo = SQLiteStudioRepository(self.db_path)
        fingerprint = approved_fingerprint(repo, owner, film_id)
        if fingerprint is None:
            return None
        film = repo.get_asset(film_id)
        return (str(film.version), fingerprint) if film is not None else None

    def enqueue(self, *, owner: str, film_id: str, fps: int = 6) -> dict:
        if fps not in (2, 6, 12):
            raise PrivateRenderQueueError("Use 2, 6 or 12 FPS")
        approved = self._approved(owner, film_id)
        if approved is None:
            raise PrivateRenderQueueError("An adult must approve the current private film")
        revision, fingerprint = approved
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """SELECT * FROM private_family_render_queue
                       WHERE owner=? AND film_id=? AND revision=? AND fingerprint=?""",
                    (owner, film_id, revision, fingerprint),
                ).fetchone()
                if row is not None:
                    # Deliberately idempotent. A failed job must be retried
                    # explicitly; duplicate clicks never bypass limits.
                    conn.execute("COMMIT")
                    return self._record(row)
                total = conn.execute(
                    """SELECT COUNT(*) FROM private_family_render_queue
                       WHERE status IN ('queued','running')"""
                ).fetchone()[0]
                own = conn.execute(
                    """SELECT COUNT(*) FROM private_family_render_queue
                       WHERE owner=? AND status IN ('queued','running')""",
                    (owner,),
                ).fetchone()[0]
                today = conn.execute(
                    """SELECT COUNT(*) FROM private_family_render_queue
                       WHERE owner=? AND created_at>=?""",
                    (owner, now - 86400),
                ).fetchone()[0]
                if (
                    total >= MAX_OUTSTANDING
                    or own >= MAX_PER_CHILD_OUTSTANDING
                    or today >= MAX_DAILY_SUBMISSIONS
                ):
                    raise PrivateRenderQueueError("Private render quota reached")
                job_id = "RENDER_" + uuid.uuid4().hex
                conn.execute(
                    """INSERT INTO private_family_render_queue
                    (job_id,owner,film_id,revision,fingerprint,fps,status,
                     attempts,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,'queued',0,?,?)""",
                    (job_id, owner, film_id, revision, fingerprint, fps, now, now),
                )
                row = conn.execute(
                    "SELECT * FROM private_family_render_queue WHERE job_id=?",
                    (job_id,),
                ).fetchone()
                conn.execute("COMMIT")
                return self._record(row)
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def claim_one(self) -> dict | None:
        """One SQLite write transaction makes exactly one claim globally.

        Read/validate canonical Character/Equipment before obtaining the
        queue write lock: that validation can lazily seed equipment in the
        main SQLite database, so running it inside BEGIN IMMEDIATE deadlocks.
        The worker independently rechecks approval at start and finish.
        """
        while True:
            with self._connect() as read:
                candidate = read.execute(
                    """SELECT * FROM private_family_render_queue
                       WHERE status='queued'
                       ORDER BY created_at,job_id LIMIT 1"""
                ).fetchone()
            if candidate is None:
                return None
            current = self._approved(candidate["owner"], candidate["film_id"])
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    busy = conn.execute(
                        "SELECT 1 FROM private_family_render_queue "
                        "WHERE status='running' LIMIT 1"
                    ).fetchone()
                    if busy:
                        conn.execute("COMMIT")
                        return None
                    row = conn.execute(
                        """SELECT * FROM private_family_render_queue
                           WHERE job_id=? AND status='queued'""",
                        (candidate["job_id"],),
                    ).fetchone()
                    if row is None:
                        conn.execute("COMMIT")
                        continue  # Claimed by another worker in the meantime.
                    if current != (row["revision"], row["fingerprint"]):
                        conn.execute(
                            """UPDATE private_family_render_queue
                               SET status='blocked',error_code='approval_changed',
                                   updated_at=? WHERE job_id=?""",
                            (time.time(), row["job_id"]),
                        )
                        conn.execute("COMMIT")
                        continue
                    conn.execute(
                        """UPDATE private_family_render_queue
                           SET status='running',attempts=attempts+1,updated_at=?
                           WHERE job_id=? AND status='queued'""",
                        (time.time(), row["job_id"]),
                    )
                    fresh = conn.execute(
                        "SELECT * FROM private_family_render_queue WHERE job_id=?",
                        (row["job_id"],),
                    ).fetchone()
                    conn.execute("COMMIT")
                    return self._record(fresh)
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

    def _finish(self, job: dict, state: str, code: str = "") -> dict:
        # Avoid deadlocking on lazy canonical Equipment writes while holding
        # a queue transaction. Download release always checks approval again.
        if state == "completed" and self._approved(
            job["owner"], job["film_id"]
        ) != (job["revision"], job["fingerprint"]):
            state, code = "blocked", "approval_changed"
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT * FROM private_family_render_queue WHERE job_id=?",
                    (job["job_id"],),
                ).fetchone()
                if row is None or row["status"] != "running":
                    raise PrivateRenderQueueError("Job no longer held by private worker")
                conn.execute(
                    """UPDATE private_family_render_queue
                       SET status=?,error_code=?,updated_at=?
                       WHERE job_id=? AND status='running'""",
                    (state, code, time.time(), job["job_id"]),
                )
                final = conn.execute(
                    "SELECT * FROM private_family_render_queue WHERE job_id=?",
                    (job["job_id"],),
                ).fetchone()
                conn.execute("COMMIT")
                return self._record(final)
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def run_one(
        self, *, project_dir: Path, store_root: Path,
        godot: str = "godot", ffmpeg: str = "ffmpeg",
        ffprobe: str = "ffprobe", xvfb_run: str = "xvfb-run",
        renderer: Callable = render_private_movie,
    ) -> dict | None:
        """Trusted single-host invocation; not reachable from the child API."""
        job = self.claim_one()
        if job is None:
            return None
        try:
            if shutil.disk_usage(store_root).free < MIN_FREE_BYTES:
                raise PrivateRenderQueueError("Insufficient private disk space")
            output = media_path(
                Path(store_root), owner=job["owner"],
                film_id=job["film_id"], fingerprint=job["fingerprint"],
                create_dirs=True,
            )
            created_output = not output.exists()
            if not created_output:
                existing = read_private_media(output)
                if existing is None:
                    raise PrivateRenderQueueError("Existing private media failed verification")
                # Parent may have rendered this exact snapshot manually.
                # No need to spend resources a second time.
            else:
                renderer(
                    db_path=self.db_path, project_dir=project_dir,
                    owner=job["owner"], film_id=job["film_id"],
                    output_path=output, fps=job["fps"],
                    godot=godot, ffmpeg=ffmpeg, ffprobe=ffprobe,
                    xvfb_run=xvfb_run,
                )
            # If revoked during execution, remove any newly rendered bytes
            # before returning a blocked status. Never release automatically.
            result = self._finish(job, "completed")
            if (
                result["status"] != "completed"
                and created_output
                and output.exists()
            ):
                output.unlink()
            return result
        except Exception:
            # Errors are deliberately reduced to a fixed code: filenames,
            # subprocess stderr, and child-authored data must never be logged.
            # Never persist arbitrary shell/Godot stderr or a child's notes.
            self._finish(job, "failed", "render_failed")
            return {**job, "status": "failed", "error_code": "render_failed"}

    def list_jobs(self, *, owner: str | None = None) -> list[dict]:
        if owner is not None and owner not in ("child_a", "child_b"):
            raise PrivateRenderQueueError("Invalid private owner")
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM private_family_render_queue
                   WHERE (? IS NULL OR owner=?)
                   ORDER BY created_at DESC, job_id DESC LIMIT 50""",
                (owner, owner),
            ).fetchall()
            return [self._record(row) for row in rows]

    def mark_interrupted_failed(self, job_id: str) -> dict:
        """Adult-only manual recovery; NEVER auto-resume potentially live work."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """UPDATE private_family_render_queue
                       SET status='failed',error_code='adult_marked_interrupted',
                           updated_at=?
                       WHERE job_id=? AND status='running'""",
                    (time.time(), job_id),
                )
                row = conn.execute(
                    "SELECT * FROM private_family_render_queue WHERE job_id=?",
                    (job_id,),
                ).fetchone()
                conn.execute("COMMIT")
                if row is None:
                    raise PrivateRenderQueueError("Unknown private render job")
                return self._record(row)
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def retry_failed(self, job_id: str) -> dict:
        """At most two paid/local attempts and only with fresh parent approval."""
        with self._connect() as read:
            candidate = read.execute(
                "SELECT * FROM private_family_render_queue WHERE job_id=?",
                (job_id,),
            ).fetchone()
        if candidate is None:
            raise PrivateRenderQueueError("Unknown private render job")
        current = self._approved(candidate["owner"], candidate["film_id"])
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT * FROM private_family_render_queue WHERE job_id=?",
                    (job_id,),
                ).fetchone()
                if (
                    row is None or row["status"] not in ("failed", "blocked")
                    or row["attempts"] >= MAX_ATTEMPTS
                    or current != (row["revision"], row["fingerprint"])
                ):
                    raise PrivateRenderQueueError(
                        "Retry requires unchanged adult approval and remaining attempts"
                    )
                outstanding = conn.execute(
                    """SELECT COUNT(*) FROM private_family_render_queue
                       WHERE status IN ('queued','running')"""
                ).fetchone()[0]
                own = conn.execute(
                    """SELECT COUNT(*) FROM private_family_render_queue
                       WHERE owner=? AND status IN ('queued','running')""",
                    (row["owner"],),
                ).fetchone()[0]
                if outstanding >= MAX_OUTSTANDING or own >= MAX_PER_CHILD_OUTSTANDING:
                    raise PrivateRenderQueueError("Private render quota reached")
                conn.execute(
                    """UPDATE private_family_render_queue
                       SET status='queued',error_code='',updated_at=?
                       WHERE job_id=?""",
                    (time.time(), job_id),
                )
                result = conn.execute(
                    "SELECT * FROM private_family_render_queue WHERE job_id=?",
                    (job_id,),
                ).fetchone()
                conn.execute("COMMIT")
                return self._record(result)
            except Exception:
                conn.execute("ROLLBACK")
                raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Adult-only private family render queue")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--store-root", type=Path)
    parser.add_argument("--godot-project", type=Path)
    parser.add_argument("--fps", type=int, choices=(2, 6, 12), default=6)
    args = parser.add_subparsers(dest="action", required=True)
    enqueue = args.add_parser("enqueue")
    enqueue.add_argument("--owner", choices=("child_a", "child_b"), required=True)
    enqueue.add_argument("--film-id", required=True)
    args.add_parser("run-one")
    args.add_parser("list")
    interrupted = args.add_parser("mark-interrupted-failed")
    interrupted.add_argument("--job-id", required=True)
    retry = args.add_parser("retry")
    retry.add_argument("--job-id", required=True)
    ns = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        parser.error("Never process real child films from public GitHub CI")
    queue = PrivateFamilyRenderQueue(ns.db)
    try:
        if ns.action == "enqueue":
            result = queue.enqueue(owner=ns.owner, film_id=ns.film_id, fps=ns.fps)
        elif ns.action == "run-one":
            if ns.store_root is None or ns.godot_project is None:
                parser.error("Run-one requires --store-root and --godot-project")
            result = queue.run_one(
                project_dir=ns.godot_project, store_root=ns.store_root
            )
        elif ns.action == "list":
            result = queue.list_jobs()
        elif ns.action == "mark-interrupted-failed":
            result = queue.mark_interrupted_failed(ns.job_id)
        else:
            result = queue.retry_failed(ns.job_id)
    except (PrivateRenderQueueError, PrivateMovieMediaError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
