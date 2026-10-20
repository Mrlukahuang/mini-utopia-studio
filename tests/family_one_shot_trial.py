"""#471 synthetic ONLY: cross-container API /data RW and /movies RO trial.

This module never accepts a database path or a host mount argument: fixed paths
are created by the one-off Docker driver in newly allocated synthetic storage.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

from studio.family_api import FamilyApplication
from studio.family_movie_media import approved_fingerprint, media_path
from studio.family_render_queue import PrivateFamilyRenderQueue, PrivateRenderQueueError
from studio.repositories.sqlite import SQLiteStudioRepository

DB = Path("/data/studio.db")
STORE = Path("/movies")
STATE = Path("/data/one-shot-synthetic-film-id")
ORIGIN = "https://family.example"
PARENT = "synthetic-adult-0123456789abcdef"
CHILD_A = "synthetic-child-a"
CHILD_B = "synthetic-child-b"


def app() -> FamilyApplication:
    return FamilyApplication(
        SQLiteStudioRepository(DB),
        token_hashes={
            "child_a": hashlib.sha256(CHILD_A.encode()).hexdigest(),
            "child_b": hashlib.sha256(CHILD_B.encode()).hexdigest(),
        },
        parent_unlock_hash=hashlib.sha256(PARENT.encode()).hexdigest(),
        allowed_origins=(ORIGIN,),
        private_movie_root=STORE,
    )


def call(application, method, route, payload=None, token=CHILD_A, *, media=None):
    return application.handle(
        method=method, path=route, origin=ORIGIN,
        authorization="Bearer " + token,
        body=media if media is not None else json.dumps(payload).encode()
        if payload is not None else b"",
        content_type="audio/wav" if media is not None else "application/json",
    )


def assert_mounts(*, api_view: bool) -> None:
    assert os.getuid() == 10001 and os.getgid() == 10001
    assert DB.parent.is_dir() and STORE.is_dir()
    assert DB.parent.stat().st_uid == 10001
    assert STORE.stat().st_uid == 10001
    assert stat.S_IMODE(STORE.stat().st_mode) == 0o700
    readonly = bool(STORE.stat().st_mode) and bool(
        os.statvfs(STORE).f_flag & getattr(os, "ST_RDONLY", 1)
    )
    assert readonly is api_view, "Worker RW / API RO topology mismatch"


def seed() -> None:
    assert_mounts(api_view=True)
    assert not DB.exists() and not STATE.exists(), "Synthetic volume reused"
    application = app()
    hero = call(application, "POST", "/characters", {
        "display_name": "Synthetic Cloud Sheep",
    })
    assert hero.status == 201
    draft = call(application, "POST", "/family/films", {
        "schema_version": "1.0",
        "display_name": "Synthetic One-Shot Mount Film",
        "character_id": hero.payload["character_id"],
        "camera": "wide", "action": "walk",
        "duration_seconds": 15, "music_id": "sunny_meadow",
    })
    assert draft.status == 201
    fid = draft.payload["film_id"]
    tone = Path("/tmp/synthetic-440hz.wav")
    subprocess.run([
        "ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi",
        "-i", "sine=frequency=440:sample_rate=16000:duration=1.3",
        "-ac", "1", "-c:a", "pcm_s16le", str(tone),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    route = f"/family/films/{fid}/voices/0?revision={draft.payload['revision']}"
    assert call(application, "POST", route, token=CHILD_B,
                media=tone.read_bytes()).status == 400
    voice = call(application, "POST", route, media=tone.read_bytes())
    assert voice.status == 201
    with sqlite3.connect(DB) as db:
        assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        db.execute("CREATE TABLE synthetic_wal_probe (marker INTEGER)")
        db.execute("INSERT INTO synthetic_wal_probe VALUES (1)")
        db.commit()
        assert DB.with_name("studio.db-wal").is_file()
        assert DB.with_name("studio.db-shm").is_file()
        assert db.execute("SELECT marker FROM synthetic_wal_probe").fetchone()[0] == 1
    queue = PrivateFamilyRenderQueue(DB)
    try:
        queue.enqueue(owner="child_a", film_id=fid, fps=2)
    except PrivateRenderQueueError:
        pass
    else:
        raise AssertionError("Unapproved enqueue was allowed")
    review = call(application, "POST", "/family/film-reviews", {
        "profile_id": "child_a", "film_id": fid,
        "revision": voice.payload["revision"], "decision": "approve",
    }, token=PARENT)
    assert review.status == 200 and review.payload["approved_for_private_render"]
    try:
        queue.enqueue(owner="child_b", film_id=fid, fps=2)
    except PrivateRenderQueueError:
        pass
    else:
        raise AssertionError("Sibling queued another owner's film")
    assert queue.enqueue(owner="child_a", film_id=fid, fps=2)["status"] == "queued"
    STATE.write_text(fid, encoding="ascii")
    STATE.chmod(0o600)
    print("SYNTHETIC_SEED_WAL_APPROVAL_QUEUED_PASS", flush=True)


def verify() -> None:
    assert_mounts(api_view=True)
    assert STATE.stat().st_uid == 10001 and stat.S_IMODE(STATE.stat().st_mode) == 0o600
    fid = STATE.read_text(encoding="ascii")
    application = app()
    queue = PrivateFamilyRenderQueue(DB)
    jobs = queue.list_jobs(owner="child_a")
    assert len(jobs) == 1 and jobs[0]["status"] == "completed", jobs
    fp = approved_fingerprint(application.repository, "child_a", fid)
    assert fp
    output = media_path(STORE, owner="child_a", film_id=fid, fingerprint=fp)
    media_stat = output.stat()
    assert media_stat.st_uid == 10001
    assert stat.S_IMODE(media_stat.st_mode) == 0o600
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_name,codec_type", "-of", "json", str(output),
    ], check=True, text=True, capture_output=True)
    info = json.loads(probe.stdout)
    assert abs(float(info["format"]["duration"]) - 15) <= 0.6
    assert len([s for s in info["streams"] if s["codec_name"] == "h264"]) == 1
    assert len([s for s in info["streams"] if s["codec_name"] == "aac"]) == 1
    assert application.private_mp4_for_download(
        authorization="Bearer " + CHILD_A, film_id=fid, origin=ORIGIN
    ) is None, "Worker completion must not release movie"
    actor = application.repository.get_asset(fid)
    choice = {"profile_id": "child_a", "film_id": fid, "revision": str(actor.version)}
    released = call(application, "POST", "/family/movie-releases", {
        **choice, "decision": "release",
    }, token=PARENT)
    assert released.status == 200 and released.payload["released_to_child"]
    assert application.private_mp4_for_download(
        authorization="Bearer " + CHILD_A, film_id=fid, origin=ORIGIN
    ) == output.read_bytes()
    assert application.private_mp4_for_download(
        authorization="Bearer " + CHILD_B, film_id=fid, origin=ORIGIN
    ) is None
    revoked = call(application, "POST", "/family/movie-releases", {
        **choice, "decision": "revoke",
    }, token=PARENT)
    assert revoked.status == 200
    assert application.private_mp4_for_download(
        authorization="Bearer " + CHILD_A, film_id=fid, origin=ORIGIN
    ) is None
    assert queue.claim_one() is None, "Completed queue must never auto-retry"
    print("SYNTHETIC_API_RO_WORKER_RW_RELEASE_OWNER_REVOKE_PASS", flush=True)


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("seed", "verify")
    {"seed": seed, "verify": verify}[sys.argv[1]]()
