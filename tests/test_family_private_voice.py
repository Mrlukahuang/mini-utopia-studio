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
