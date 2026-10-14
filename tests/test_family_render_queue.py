"""Synthetic, network-free tests of the private parent-reviewed render queue."""
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from studio.family_api import FamilyApplication
from studio.family_movie_review import decide_private_film_review
from studio.family_render_queue import (
    MAX_ATTEMPTS, PrivateFamilyRenderQueue, PrivateRenderQueueError,
)
from studio.repositories.sqlite import SQLiteStudioRepository


ORIGIN = "https://family.example"
VIDEO = b"\x00\x00\x00\x18ftypisom" + b"0" * 1024


def create_fixture(tmp_path):
    db = tmp_path / "family.db"
    media = tmp_path / "private-movies"
    media.mkdir(mode=0o700)
    app = FamilyApplication(
        SQLiteStudioRepository(db),
        token_hashes={
            "child_a": hashlib.sha256(b"synthetic-child-a").hexdigest(),
            "child_b": hashlib.sha256(b"synthetic-child-b").hexdigest(),
        },
        allowed_origins=(ORIGIN,),
    )

    def make_film(owner="child_a"):
        token = "synthetic-child-a" if owner == "child_a" else "synthetic-child-b"
        def send(method, route, data):
            return app.handle(
                method=method, path=route,
                origin=ORIGIN, authorization="Bearer " + token,
                body=json.dumps(data).encode(),
            )
        hero = send("POST", "/characters", {"display_name": "Synthetic actor"})
        assert hero.status == 201
        film = send("POST", "/family/films", {
            "schema_version": "1.0",
            "display_name": "Synthetic private story",
            "character_id": hero.payload["character_id"],
            "camera": "wide", "action": "walk",
            "duration_seconds": 15,
        })
        assert film.status == 201
        return film.payload

    return db, media, app, make_film


def approve(app, film, owner="child_a", decision="approve"):
    state = decide_private_film_review(
        app.repository, owner=owner, film_id=film["film_id"],
        revision=film["revision"], decision=decision,
    )
    assert state is not None
    return state


def test_no_child_can_enqueue_without_exact_parent_approval(tmp_path):
    db, _media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    queue = PrivateFamilyRenderQueue(db)
    with pytest.raises(PrivateRenderQueueError, match="adult"):
        queue.enqueue(owner="child_a", film_id=film["film_id"])
    with pytest.raises(PrivateRenderQueueError, match="adult"):
        queue.enqueue(owner="child_b", film_id=film["film_id"])
    approve(app, film)
    with pytest.raises(PrivateRenderQueueError, match="adult"):
        queue.enqueue(owner="child_b", film_id=film["film_id"])
    with pytest.raises(PrivateRenderQueueError, match="FPS"):
        queue.enqueue(owner="child_a", film_id=film["film_id"], fps=60)
    job = queue.enqueue(owner="child_a", film_id=film["film_id"], fps=2)
    assert job["status"] == "queued"
    assert job["revision"] == film["revision"]
    assert job["fingerprint"]
    assert queue.enqueue(owner="child_a", film_id=film["film_id"]) == job
    assert len(PrivateFamilyRenderQueue(db).list_jobs(owner="child_a")) == 1
    assert PrivateFamilyRenderQueue(db).list_jobs(owner="child_b") == []
    assert "private_story_note" not in json.dumps(job)


def test_atomic_claim_is_singleton_across_concurrent_worker_instances(tmp_path):
    db, _media, app, make_film = create_fixture(tmp_path)
    a = make_film()
    b = make_film("child_b")
    approve(app, a)
    approve(app, b, "child_b")
    queue = PrivateFamilyRenderQueue(db)
    queue.enqueue(owner="child_a", film_id=a["film_id"])
    queue.enqueue(owner="child_b", film_id=b["film_id"])

    def claim():
        return PrivateFamilyRenderQueue(db).claim_one()

    with ThreadPoolExecutor(max_workers=6) as executor:
        attempted = list(executor.map(lambda _: claim(), range(6)))
    granted = [record for record in attempted if record is not None]
    assert len(granted) == 1, "Only one private Godot render at a time"
    assert granted[0]["attempts"] == 1
    assert PrivateFamilyRenderQueue(db).claim_one() is None
    queue.mark_interrupted_failed(granted[0]["job_id"])
    second = queue.claim_one()
    assert second is not None
    assert second["job_id"] != granted[0]["job_id"]


def test_revoked_before_claim_is_blocked_without_worker_invocation(tmp_path):
    db, _media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    original = queue.enqueue(owner="child_a", film_id=film["film_id"])
    approve(app, film, decision="revoke")
    assert queue.claim_one() is None
    latest = queue.list_jobs()[0]
    assert latest["job_id"] == original["job_id"]
    assert latest["status"] == "blocked"
    assert latest["error_code"] == "approval_changed"
    with pytest.raises(PrivateRenderQueueError, match="approval"):
        queue.retry_failed(latest["job_id"])


def test_actual_queue_execution_is_private_and_never_auto_releases(tmp_path):
    db, media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    job = queue.enqueue(owner="child_a", film_id=film["film_id"], fps=2)
    invoked = []

    def render(**kwargs):
        invoked.append(kwargs)
        path = kwargs["output_path"]
        assert path.parent.stat().st_mode & 0o077 == 0
        assert kwargs["owner"] == "child_a"
        assert kwargs["film_id"] == film["film_id"]
        assert kwargs["fps"] == 2
        path.write_bytes(VIDEO)
        path.chmod(0o600)
        return {"bytes": len(VIDEO)}

    finished = queue.run_one(
        project_dir=tmp_path, store_root=media, renderer=render,
    )
    assert finished["status"] == "completed"
    assert finished["job_id"] == job["job_id"]
    assert len(invoked) == 1
    assert queue.run_one(project_dir=tmp_path, store_root=media, renderer=render) is None
    assert len(invoked) == 1
    assert app.private_mp4_for_download(
        authorization="Bearer synthetic-child-a", film_id=film["film_id"],
        origin=ORIGIN,
    ) is None, "Worker completion never grants child download permission"


def test_parent_revoking_during_render_prevents_completed_job_and_file(tmp_path):
    db, media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    queue.enqueue(owner="child_a", film_id=film["film_id"])

    def render(**kwargs):
        output = kwargs["output_path"]
        output.write_bytes(VIDEO)
        output.chmod(0o600)
        approve(app, film, decision="revoke")

    result = queue.run_one(
        project_dir=tmp_path, store_root=media, renderer=render,
    )
    assert result["status"] == "blocked"
    assert result["error_code"] == "approval_changed"
    from studio.family_movie_media import media_path
    output = media_path(
        media, owner="child_a", film_id=film["film_id"],
        fingerprint=result["fingerprint"],
    )
    assert not output.exists()
    assert app.private_mp4_for_download(
        authorization="Bearer synthetic-child-a",
        film_id=film["film_id"], origin=ORIGIN
    ) is None


def test_failed_worker_requires_explicit_retry_with_at_most_two_attempts(tmp_path):
    db, media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    first = queue.enqueue(owner="child_a", film_id=film["film_id"])

    def fail(**kwargs):
        raise RuntimeError("Never save subprocess stdout or user film metadata")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        outcome = queue.run_one(
            project_dir=tmp_path, store_root=media, renderer=fail,
        )
        assert outcome["status"] == "failed"
        assert "subprocess" not in json.dumps(queue.list_jobs())
        assert queue.list_jobs()[0]["attempts"] == attempt
        assert queue.run_one(
            project_dir=tmp_path, store_root=media, renderer=fail,
        ) is None, "No automatic retry after a private render fails"
        if attempt < MAX_ATTEMPTS:
            recovered = queue.retry_failed(first["job_id"])
            assert recovered["status"] == "queued"
    with pytest.raises(PrivateRenderQueueError, match="remaining attempts"):
        queue.retry_failed(first["job_id"])


def test_queue_per_child_quota_blocks_flood_even_with_valid_review(tmp_path):
    db, _media, app, make_film = create_fixture(tmp_path)
    films = [make_film() for _ in range(3)]
    for item in films:
        approve(app, item)
    queue = PrivateFamilyRenderQueue(db)
    assert queue.enqueue(owner="child_a", film_id=films[0]["film_id"])
    assert queue.enqueue(owner="child_a", film_id=films[1]["film_id"])
    with pytest.raises(PrivateRenderQueueError, match="quota"):
        queue.enqueue(owner="child_a", film_id=films[2]["film_id"])


def test_database_restart_does_not_silently_restart_abandoned_render(tmp_path):
    db, _media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    queued = queue.enqueue(owner="child_a", film_id=film["film_id"])
    claimed = queue.claim_one()
    assert claimed["job_id"] == queued["job_id"]
    restarted = PrivateFamilyRenderQueue(db)
    assert restarted.claim_one() is None
    assert restarted.list_jobs()[0]["status"] == "running"
    assert restarted.mark_interrupted_failed(queued["job_id"])["status"] == "failed"
    assert restarted.retry_failed(queued["job_id"])["status"] == "queued"
    assert restarted.claim_one()["attempts"] == 2


@pytest.mark.parametrize(
    "failure_mode",
    ("partial_then_raise", "valid_then_raise", "invalid_success", "missing_success"),
)
def test_failed_render_removes_new_private_media_and_allows_manual_retry(
    tmp_path, failure_mode
):
    db, media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    queued = queue.enqueue(owner="child_a", film_id=film["film_id"])

    from studio.family_movie_media import media_path

    path = media_path(
        media, owner="child_a", film_id=film["film_id"],
        fingerprint=queued["fingerprint"], create_dirs=True,
    )

    def broken_render(**kwargs):
        if failure_mode != "missing_success":
            payload = VIDEO if failure_mode == "valid_then_raise" else b"partial"
            kwargs["output_path"].write_bytes(payload)
            kwargs["output_path"].chmod(0o600)
        if failure_mode.endswith("_raise"):
            raise RuntimeError("Private child story must not leak to queue logs")

    failed = queue.run_one(
        project_dir=tmp_path, store_root=media, renderer=broken_render,
    )
    assert failed["status"] == "failed"
    assert failed["error_code"] == "render_failed"
    assert not path.exists(), "An incomplete movie must not poison the next retry"
    assert "Private child story" not in json.dumps(queue.list_jobs())
    assert queue.run_one(
        project_dir=tmp_path, store_root=media, renderer=broken_render,
    ) is None, "Never retry failed rendering without an adult action"

    retry = queue.retry_failed(queued["job_id"])
    assert retry["status"] == "queued"

    def good_render(**kwargs):
        kwargs["output_path"].write_bytes(VIDEO)
        kwargs["output_path"].chmod(0o600)

    completed = queue.run_one(
        project_dir=tmp_path, store_root=media, renderer=good_render,
    )
    assert completed["status"] == "completed"
    assert completed["attempts"] == 2
    assert path.read_bytes() == VIDEO


def test_existing_verified_parent_render_is_reused_without_overwrite(tmp_path):
    db, media, app, make_film = create_fixture(tmp_path)
    film = make_film()
    approve(app, film)
    queue = PrivateFamilyRenderQueue(db)
    queued = queue.enqueue(owner="child_a", film_id=film["film_id"])

    from studio.family_movie_media import media_path

    path = media_path(
        media, owner="child_a", film_id=film["film_id"],
        fingerprint=queued["fingerprint"], create_dirs=True,
    )
    path.write_bytes(VIDEO)
    path.chmod(0o600)

    def never_render(**kwargs):
        raise AssertionError("Already verified MP4 must not be rendered again")

    result = queue.run_one(
        project_dir=tmp_path, store_root=media, renderer=never_render,
    )
    assert result["status"] == "completed"
    assert path.read_bytes() == VIDEO
