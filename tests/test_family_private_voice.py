"""Synthetic only: verify voice ownership, revision binding and AAC wiring."""
import hashlib
import json
import os
from pathlib import Path
from subprocess import CompletedProcess

from studio.family_api import FamilyApplication
from studio.family_film_render import build_family_film_render_source
from studio.family_movie_review import current_review_state, decide_private_film_review
from studio.family_music_mix import private_movie_ffmpeg_args
from studio.family_voice_policy import read_private_shot_voice
from studio.repositories.sqlite import SQLiteStudioRepository


def app_for(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "family.db")
    return FamilyApplication(
        repo,
        token_hashes={
            "child_a": hashlib.sha256(b"synthetic-a").hexdigest(),
            "child_b": hashlib.sha256(b"synthetic-b").hexdigest(),
        },
        allowed_origins=("https://family.example",),
    )


def call(app, method, route, body=b"", owner="child_a", mime=""):
    return app.handle(
        method=method, path=route,
        authorization="Bearer " + ("synthetic-a" if owner == "child_a" else "synthetic-b"),
        origin="https://family.example", body=body, content_type=mime,
    )


def synthetic_probe(*args, **kwargs):
    return CompletedProcess(args[0], 0, stdout=json.dumps({
        "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le",
                     "channels": 1, "sample_rate": "16000"}],
        "format": {"duration": "1.5"},
    }))


def test_owner_voice_upload_is_immutable_and_invalidates_parent_review(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", synthetic_probe)
    app = app_for(tmp_path)
    a = call(app, "POST", "/characters", json.dumps({"display_name": "A"}).encode()).payload
    b = call(app, "POST", "/characters", json.dumps({"display_name": "B"}).encode(),
             owner="child_b").payload
    film = call(app, "POST", "/family/films", json.dumps({
        "display_name": "Synthetic film", "character_id": a["character_id"],
    }).encode()).payload
    fid = film["film_id"]
    route = "/family/films/" + fid + "/voices/0"
    blob = b"RIFF" + b"\0" * 2000  # Fake bytes: metadata is mocked, never a child voice.
    assert call(app, "POST", route, blob, owner="child_b", mime="audio/wav").status == 400
    assert call(app, "POST", route, blob, mime="video/mp4").status == 400
    assert call(app, "POST", route.replace("/0", "/1"), blob,
                mime="audio/wav").status == 400
    assert call(app, "POST", route, b"x" * 1_500_001, mime="audio/wav").status == 400
    uploaded = call(app, "POST", route, blob, mime="audio/wav")
    assert uploaded.status == 201
    assert uploaded.payload["revision"] == "2"
    source = build_family_film_render_source(app.repository, owner="child_a", film_id=fid)
    clip = source["voice_clips"]["0"]
    assert clip["sha256"] == hashlib.sha256(blob).hexdigest()
    root = tmp_path / "voice-clips"
    assert read_private_shot_voice(root, owner="child_a", film_id=fid, clip=clip) == blob
    assert not (root / "child_b" / fid).exists()
    files = list((root / "child_a" / fid).glob("*.wav"))
    assert len(files) == 1 and os.stat(files[0]).st_mode & 0o077 == 0
    assert current_review_state(app.repository, owner="child_a", film_id=fid)[
        "requires_parent_review"
    ]
    reviewed = decide_private_film_review(
        app.repository, owner="child_a", film_id=fid,
        revision="2", decision="approve",
    )
    assert reviewed["approved_for_private_render"]

    next_blob = blob + b"more synthetic samples"
    after = call(app, "POST", route, next_blob, mime="audio/wav")
    assert after.status == 201 and after.payload["revision"] == "3"
    assert not current_review_state(app.repository, owner="child_a", film_id=fid)[
        "approved_for_private_render"
    ]
    assert len(list((root / "child_a" / fid).glob("*.wav"))) == 2
    assert call(app, "GET", "/family/films/" + fid, owner="child_b").status == 404
    assert call(app, "POST", "/family/films", json.dumps({
        "display_name": "bad", "character_id": b["character_id"],
    }).encode(), owner="child_a").status == 404


def test_private_voice_renders_as_aac_single_stream(tmp_path):
    frames = tmp_path / "frame_%05d.png"
    output = tmp_path / "private.mp4"
    voice = tmp_path / "shot_00.wav"
    args = private_movie_ffmpeg_args(
        project_root=tmp_path, frames_pattern=frames, destination=output,
        music_id="none", duration_seconds=15, fps=6, voice_file=voice,
    )
    assert ["-map", "1:a:0"] == args[args.index("-map", args.index("-map") + 1):
                                           args.index("-map", args.index("-map") + 1) + 2]
    assert "aac" in args and str(voice) in args
    silent = private_movie_ffmpeg_args(
        project_root=tmp_path, frames_pattern=frames, destination=output,
        music_id="none", duration_seconds=15, fps=6,
    )
    assert "-c:a" not in silent and str(voice) not in silent


def test_pinned_revision_rejects_stale_voice_without_creating_a_second_clip(
    tmp_path, monkeypatch
):
    import subprocess
    monkeypatch.setattr(subprocess, "run", synthetic_probe)
    app = app_for(tmp_path)
    hero = call(app, "POST", "/characters", json.dumps({
        "display_name": "Synthetic hero",
    }).encode()).payload
    film = call(app, "POST", "/family/films", json.dumps({
        "display_name": "Synthetic shot", "character_id": hero["character_id"],
    }).encode()).payload
    fid = film["film_id"]
    route = f"/family/films/{fid}/voices/0"
    body = b"RIFF" + b"z" * 2000
    wrong_owner = call(
        app, "POST", route + "?revision=1", body,
        owner="child_b", mime="audio/wav",
    )
    assert wrong_owner.status == 400
    bad_query = call(
        app, "POST", route + "?revision=1&revision=2", body,
        mime="audio/wav",
    )
    assert bad_query.status == 400
    first = call(app, "POST", route + "?revision=1", body, mime="audio/wav")
    assert first.status == 201 and first.payload["revision"] == "2"
    root = tmp_path / "voice-clips" / "child_a" / fid
    assert len(list(root.glob("*.wav"))) == 1
    stale = call(app, "POST", route + "?revision=1", body + b"x", mime="audio/wav")
    assert stale.status == 409 and stale.payload["error"] == "film_revision_conflict"
    assert len(list(root.glob("*.wav"))) == 1
    current = call(app, "POST", route + "?revision=2", body + b"x", mime="audio/wav")
    assert current.status == 201 and current.payload["revision"] == "3"
    assert len(list(root.glob("*.wav"))) == 2


def test_real_synthetic_voice_bytes_probe_and_owner_storage(tmp_path):
    """Use actual FFmpeg/FFprobe instead of mocked metadata; no child material."""
    import shutil
    import subprocess
    import pytest

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Real synthetic media verification needs FFmpeg and FFprobe")
    app = app_for(tmp_path)
    hero = call(app, "POST", "/characters", json.dumps({
        "display_name": "Synthetic hero",
    }).encode()).payload
    film = call(app, "POST", "/family/films", json.dumps({
        "display_name": "Synthetic film", "character_id": hero["character_id"],
    }).encode()).payload
    fid = film["film_id"]
    route = f"/family/films/{fid}/voices/0?revision=1"
    wav = tmp_path / "synthetic-tone.wav"
    subprocess.run([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=1.3",
        "-ac", "1", "-c:a", "pcm_s16le", str(wav),
    ], check=True, timeout=20)
    blob = wav.read_bytes()
    assert 0 < len(blob) < 1_500_000
    saved = call(app, "POST", route, blob, mime="audio/wav")
    assert saved.status == 201
    assert saved.payload["shot_index"] == 0
    assert 1.2 <= saved.payload["duration_seconds"] <= 1.4
    source = build_family_film_render_source(
        app.repository, owner="child_a", film_id=fid
    )
    clip = source["voice_clips"]["0"]
    assert read_private_shot_voice(
        tmp_path / "voice-clips", owner="child_a", film_id=fid, clip=clip
    ) == blob
    assert not (tmp_path / "voice-clips" / "child_b" / fid).exists()
