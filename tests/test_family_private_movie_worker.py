import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from studio.family_api import FamilyApplication
from studio.family_private_movie_worker import PrivateMovieError, render_private_movie
from studio.family_movie_review import decide_private_film_review
from studio.repositories.sqlite import SQLiteStudioRepository


def app_for(path):
    return FamilyApplication(
        SQLiteStudioRepository(path),
        token_hashes={
            "child_a": hashlib.sha256(b"synthetic-private-a").hexdigest(),
            "child_b": hashlib.sha256(b"synthetic-private-b").hexdigest(),
        },
        allowed_origins=("https://family.example",),
    )


def call(app, method, path, data=None):
    return app.handle(
        method=method, path=path,
        origin="https://family.example",
        authorization="Bearer synthetic-private-a",
        body=json.dumps(data).encode() if data is not None else b"",
    )


def fixture_film(tmp_path):
    db = tmp_path / "family.db"
    api = app_for(db)
    hero = call(api, "POST", "/characters", {"display_name": "Synthetic Sheep"})
    cid = hero.payload["character_id"]
    saved = call(api, "POST", "/family/films", {
        "schema_version": "1.0", "display_name": "Moon Movie",
        "character_id": cid, "camera": "wide",
        "action": "run", "duration_seconds": 15,
        "private_story_note": "This is a private idea, not public CI content",
    })
    assert saved.status == 201
    approval = decide_private_film_review(
        api.repository, owner="child_a",
        film_id=saved.payload["film_id"],
        revision=saved.payload["revision"], decision="approve",
    )
    assert approval["approved_for_private_render"]
    repo = tmp_path / "fake_checkout"
    project = repo / "godot"
    project.mkdir(parents=True)
    (project / "project.godot").write_text("config_version=5\n")
    (project / "runtime_state").mkdir()
    (project / "runtime_state" / "never_copy_private_data.txt").write_text("SECRET")
    private = tmp_path / "private_movies"
    private.mkdir(mode=0o700)
    return db, project, private, saved.payload["film_id"], cid


def test_isolated_private_render_worker_never_uses_repo_or_public_artifacts(tmp_path):
    db, project, private, film_id, cid = fixture_film(tmp_path)
    output = private / "private-episode.mp4"
    observed = {"commands": [], "workspaces": []}

    def fake_runner(argv, *, check, capture_output, text, timeout):
        assert check and capture_output and text and timeout == 1800
        observed["commands"].append(argv)
        if "--path" in argv:
            root = Path(argv[argv.index("--path") + 1])
            observed["workspaces"].append(root)
            assert root != project
            assert project not in root.parents
            assert not (root / "runtime_state" / "never_copy_private_data.txt").exists()
            if "res://scripts/family_movie_prepare.gd" in argv:
                source = json.loads((root / "runtime_state" /
                                     "family_movie_export_request.json").read_text())
                assert source["character"]["character_id"] == cid
                assert source["director_choices"]["camera"] == "wide"
                assert source["director_choices"]["duration_seconds"] == 15
                assert source["fps"] == 2
                assert "private_story_note" not in json.dumps(source)
                request = {
                    "frame_count": 30, "fps": 2,
                    "director_session": {"character_asset_id": cid},
                }
                (root / "runtime_state" / "shot_capture_request.json").write_text(
                    json.dumps(request)
                )
            if "res://scripts/shot_frame_capture.gd" in argv:
                frames = root / "runtime_state" / "family_movie_frames" / "EP_FAMILY_PREVIEW"
                frames.mkdir(parents=True)
                for i in range(30):
                    (frames / f"frame_{i:05d}.png").write_bytes(b"PNG")
        if argv[0] == "ffmpeg":
            Path(argv[-1]).write_bytes(b"\x00\x00\x00\x18ftypisom" + b"0" * 800)
        return subprocess.CompletedProcess(
            argv, 0, stdout=(json.dumps({"streams": []}) if argv[0] == "ffprobe" and "-select_streams" in argv else "15.0\n") if argv[0] == "ffprobe" else ""
        )

    result = render_private_movie(
        db_path=db, project_dir=project, film_id=film_id,
        owner="child_a", output_path=output,
        godot="godot-test", ffmpeg="ffmpeg", ffprobe="ffprobe",
        xvfb_run="xvfb-run", fps=2, runner=fake_runner,
    )
    assert result["film_id"] == film_id
    assert result["duration_seconds"] == 15
    assert result["bytes"] > 256
    assert output.exists() and output.stat().st_mode & 0o077 == 0
    assert len(observed["commands"]) == 5
    assert any("res://scripts/shot_frame_capture.gd" in cmd for cmd in observed["commands"])
    assert (project / "runtime_state" / "never_copy_private_data.txt").read_text() == "SECRET"
    assert not (project / "runtime_state" / "shot_capture_request.json").exists()
    for root in observed["workspaces"]:
        assert not root.exists(), "temporary private film source/frames must be deleted"


def test_worker_rejects_wrong_child_public_folder_overwrite_and_bad_rate(tmp_path):
    db, project, private, film_id, _cid = fixture_film(tmp_path)
    output = private / "saved.mp4"
    common = dict(
        db_path=db, project_dir=project, film_id=film_id,
        output_path=output, owner="child_a",
    )
    with pytest.raises(PrivateMovieError, match="owned"):
        render_private_movie(**{**common, "owner": "child_b"})
    with pytest.raises(PrivateMovieError, match="Git checkout"):
        render_private_movie(**{**common, "output_path": project.parent / "public.mp4"})
    with pytest.raises(PrivateMovieError, match="FPS"):
        render_private_movie(**{**common, "fps": 60})
    output.write_bytes(b"Existing safe video")
    with pytest.raises(PrivateMovieError, match="overwrite"):
        render_private_movie(**common)

    output.unlink()
    private.chmod(0o755)
    with pytest.raises(PrivateMovieError, match="chmod 700"):
        render_private_movie(**common)


def test_parent_revocation_mid_render_cannot_publish_completed_mp4(tmp_path):
    db, project, private, film_id, cid = fixture_film(tmp_path)
    output = private / "never-published.mp4"
    observed_roots = []

    def parent_revokes_while_godot_runs(argv, *, check, capture_output, text, timeout):
        if "--path" in argv:
            workspace = Path(argv[argv.index("--path") + 1])
            observed_roots.append(workspace)
            state = workspace / "runtime_state"
            if "res://scripts/family_movie_prepare.gd" in argv:
                (state / "shot_capture_request.json").write_text(json.dumps({
                    "fps": 2, "frame_count": 30,
                    "director_session": {"character_asset_id": cid}
                }))
            elif "res://scripts/shot_frame_capture.gd" in argv:
                folder = state / "family_movie_frames" / "EP_FAMILY_PREVIEW"
                folder.mkdir(parents=True)
                for n in range(30):
                    (folder / f"frame_{n:05d}.png").write_bytes(b"PNG")
        if argv[0] == "ffmpeg":
            Path(argv[-1]).write_bytes(b"\x00\x00\x00\x18ftypisom" + b"0" * 512)
        if argv[0] == "ffprobe":
            # A parent has revoked access before the render finishes.
            revoked = decide_private_film_review(
                SQLiteStudioRepository(db), owner="child_a",
                film_id=film_id, revision="1", decision="revoke",
            )
            assert revoked["approved_for_private_render"] is False
        return subprocess.CompletedProcess(
            argv, 0, stdout=(json.dumps({"streams": []}) if argv[0] == "ffprobe" and "-select_streams" in argv else "15.0\n") if argv[0] == "ffprobe" else ""
        )

    with pytest.raises(PrivateMovieError, match="changed during rendering"):
        render_private_movie(
            db_path=db, project_dir=project, film_id=film_id,
            owner="child_a", output_path=output,
            godot="godot-test", ffmpeg="ffmpeg", ffprobe="ffprobe",
            xvfb_run="xvfb-run", fps=2, runner=parent_revokes_while_godot_runs,
        )
    assert not output.exists(), "Revoked film must never be published"
    assert observed_roots and all(not root.exists() for root in observed_roots)


def test_oversized_render_is_rejected_before_private_release(tmp_path):
    db, project, private, film_id, cid = fixture_film(tmp_path)
    output = private / "too-large.mp4"

    def fake_oversized_render(argv, *, check, capture_output, text, timeout):
        if "--path" in argv:
            workspace = Path(argv[argv.index("--path") + 1])
            state = workspace / "runtime_state"
            if "res://scripts/family_movie_prepare.gd" in argv:
                (state / "shot_capture_request.json").write_text(json.dumps({
                    "fps": 2, "frame_count": 30,
                    "director_session": {"character_asset_id": cid}
                }))
            elif "res://scripts/shot_frame_capture.gd" in argv:
                folder = state / "family_movie_frames" / "EP_FAMILY_PREVIEW"
                folder.mkdir(parents=True)
                for n in range(30):
                    (folder / f"frame_{n:05d}.png").write_bytes(b"PNG")
        if argv[0] == "ffmpeg":
            with Path(argv[-1]).open("wb") as movie:
                movie.write(b"\x00\x00\x00\x18ftypisom")
                movie.truncate(32 * 1024 * 1024 + 1)
        return subprocess.CompletedProcess(
            argv, 0, stdout=(json.dumps({"streams": []}) if argv[0] == "ffprobe" and "-select_streams" in argv else "15.0\n") if argv[0] == "ffprobe" else ""
        )

    with pytest.raises(PrivateMovieError, match="32 MiB"):
        render_private_movie(
            db_path=db, project_dir=project, film_id=film_id,
            owner="child_a", output_path=output,
            godot="godot-test", ffmpeg="ffmpeg", ffprobe="ffprobe",
            xvfb_run="xvfb-run", fps=2, runner=fake_oversized_render,
        )
    assert not output.exists()


def test_background_music_uses_whitelisted_wav_and_requires_actual_aac(tmp_path, monkeypatch):
    from studio import family_private_movie_worker as module
    db, project, private, film_id, cid = fixture_film(tmp_path)
    original_source = module.build_family_film_render_source

    # CI uses only a synthetic catalog WAV, not a child's audio or private film.
    wav = project / "assets" / "audio" / "cc0_music" / "sunny_meadow.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"RIFF" + b"\0" * 64)

    def selected_music_source(repository, *, owner, film_id):
        source = original_source(repository, owner=owner, film_id=film_id)
        if source is not None:
            source["director_choices"]["music_id"] = "sunny_meadow"
        return source

    monkeypatch.setattr(module, "build_family_film_render_source", selected_music_source)
    audio_commands = []

    def synthetic_render(argv, *, check, capture_output, text, timeout):
        if "--path" in argv:
            workspace = Path(argv[argv.index("--path") + 1])
            state = workspace / "runtime_state"
            if "res://scripts/family_movie_prepare.gd" in argv:
                (state / "shot_capture_request.json").write_text(json.dumps({
                    "fps": 2, "frame_count": 30,
                    "director_session": {"character_asset_id": cid}
                }))
            elif "res://scripts/shot_frame_capture.gd" in argv:
                frames = state / "family_movie_frames" / "EP_FAMILY_PREVIEW"
                frames.mkdir(parents=True)
                for i in range(30):
                    (frames / f"frame_{i:05d}.png").write_bytes(b"PNG")
        if argv[0] == "ffmpeg":
            audio_commands.append(argv)
            assert "-stream_loop" in argv and "-c:a" in argv
            assert "sunny_meadow.wav" in " ".join(argv)
            Path(argv[-1]).write_bytes(b"\x00\x00\x00\x18ftypisom" + b"0" * 900)
        if argv[0] == "ffprobe":
            codec = "-select_streams" in argv
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps({"streams": [{"codec_name": "aac", "start_time": "0.0", "duration": "15.0"}]}) if codec else "15.0\n"
            )
        return subprocess.CompletedProcess(argv, 0, stdout="")

    output = private / "music.mp4"
    result = render_private_movie(
        db_path=db, project_dir=project, film_id=film_id,
        owner="child_a", output_path=output, fps=2,
        runner=synthetic_render,
    )
    assert result["duration_seconds"] == 15
    assert len(audio_commands) == 1
    assert output.is_file() and output.stat().st_mode & 0o077 == 0

    # A missing AAC track must block publishing even when FFmpeg returns 0.
    output.unlink()
    def no_audio(argv, **kwargs):
        result = synthetic_render(argv, **kwargs)
        if argv[0] == "ffprobe" and "-select_streams" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="")
        return result

    with pytest.raises(PrivateMovieError, match="AAC"):
        render_private_movie(
            db_path=db, project_dir=project, film_id=film_id,
            owner="child_a", output_path=output, fps=2,
            runner=no_audio,
        )
    assert not output.exists()
