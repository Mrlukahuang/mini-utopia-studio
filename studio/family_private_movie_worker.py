"""Adult-operated local/private MP4 worker for canonical saved Family films.

Not an HTTP endpoint or an automatic public CI workflow. All scene files,
JSON contracts, PNG frames and MP4 staging live in one 0700 temporary
directory OUTSIDE the git checkout, removed even when rendering fails.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from studio.family_film_render import build_family_film_render_source
from studio.family_voice_policy import read_private_shot_voice, voice_path_relative
from studio.family_music_mix import FamilyMusicMixError, private_movie_ffmpeg_args
from studio.family_movie_review import current_review_state
from studio.family_movie_media import (
    MAX_PRIVATE_MP4_BYTES, PrivateMovieMediaError, approved_fingerprint, media_path,
)
from studio.repositories.sqlite import SQLiteStudioRepository


class PrivateMovieError(RuntimeError):
    """Expected failure without leaking child data in logs."""


def _private_output_path(project: Path, output: Path) -> Path:
    if not output.is_absolute() or output.suffix.lower() != ".mp4":
        raise PrivateMovieError("Provide an absolute private .mp4 output path")
    if not project.is_dir() or not (project / "project.godot").is_file():
        raise PrivateMovieError("Godot project directory is missing")
    # Git repos and checked-in Godot runtime_state may never be destinations.
    repo_root = project.resolve().parent
    target = output.resolve(strict=False)
    if target == repo_root or repo_root in target.parents:
        raise PrivateMovieError("Never write child video inside the Git checkout")
    if output.is_symlink() or target.exists():
        raise PrivateMovieError("Refusing to overwrite an existing movie")
    folder = output.parent.resolve()
    if not folder.is_dir():
        raise PrivateMovieError("Create a private output folder first")
    if os.name == "posix":
        st = folder.stat()
        if st.st_uid != os.getuid() or (st.st_mode & 0o077):
            raise PrivateMovieError("Output directory must be owned and chmod 700")
    return target


def _run_checked(
    argv: list[str],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(
            argv, check=True, capture_output=True, text=True, timeout=1800
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise PrivateMovieError("Private movie command failed; check host tools") from exc
    return result


def render_private_movie(
    *,
    db_path: Path,
    project_dir: Path,
    film_id: str,
    owner: str,
    output_path: Path,
    godot: str = "godot",
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    xvfb_run: str = "xvfb-run",
    fps: int = 6,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict:
    """Render a saved owner-scoped FILM with its CURRENT saved Hero and clothes.

    Requires an adult with local access to the private SQLite DB and binaries.
    Never accepts client-posted Character JSON or a raw guest's outfit.
    """
    if owner not in {"child_a", "child_b"}:
        raise PrivateMovieError("Invalid private owner profile")
    if not film_id.startswith("FILM_") or "/" in film_id:
        raise PrivateMovieError("Invalid saved film ID")
    if fps not in (2, 6, 12):
        raise PrivateMovieError("Use bounded rendering FPS of 2, 6, or 12")

    project = Path(project_dir).resolve()
    output = _private_output_path(project, Path(output_path))
    if not Path(db_path).is_file():
        raise PrivateMovieError("Family database does not exist")
    repository = SQLiteStudioRepository(Path(db_path))
    review = current_review_state(
        repository, owner=owner, film_id=film_id
    )
    if review is None:
        raise PrivateMovieError("Film or one of its actors is not currently owned")
    if not review["approved_for_private_render"]:
        raise PrivateMovieError("Current film and outfits require explicit parent approval")
    source = build_family_film_render_source(
        repository, owner=owner, film_id=film_id
    )
    if source is None or source["source_revision"] != review["revision"]:
        raise PrivateMovieError("Film or owned render inputs changed after review")
    seconds = int(source["director_choices"]["duration_seconds"])
    if seconds not in (15, 30):
        raise PrivateMovieError("Invalid family film duration")
    reviewed_source = json.loads(json.dumps(source))  # immutable snapshot for race check
    source["fps"] = fps
    source["width"] = 640
    source["height"] = 360

    with tempfile.TemporaryDirectory(prefix="mini-utopia-private-film-") as temp:
        sandbox = Path(temp)
        sandbox.chmod(0o700)
        workspace = sandbox / "godot"
        shutil.copytree(
            project, workspace,
            ignore=shutil.ignore_patterns(
                ".git", ".godot", "runtime_state", "*.log"
            ),
        )
        state = workspace / "runtime_state"
        state.mkdir(mode=0o700)
        request_file = state / "family_movie_export_request.json"
        request_file.write_text(json.dumps(source), encoding="utf-8")
        request_file.chmod(0o600)

        # Import the isolated project before running any scene scripts.
        # None of these subprocesses receives a child's access token.
        _run_checked(
            [godot, "--headless", "--path", str(workspace),
             "--editor", "--quit"],
            runner,
        )
        _run_checked(
            [godot, "--headless", "--path", str(workspace),
             "--script", "res://scripts/family_movie_prepare.gd"],
            runner,
        )
        request = state / "shot_capture_request.json"
        if not request.is_file():
            raise PrivateMovieError("Private Godot render manifest missing")
        try:
            capture = json.loads(request.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise PrivateMovieError("Invalid private capture manifest") from exc
        if (
            capture.get("frame_count") != seconds * fps
            or capture.get("fps") != fps
            or capture.get("director_session", {}).get("character_asset_id")
            != source["character"]["character_id"]
        ):
            raise PrivateMovieError("Render manifest diverged from saved film")

        _run_checked(
            [xvfb_run, "-a", godot, "--path", str(workspace),
             "--rendering-method", "gl_compatibility", "--resolution",
             "640x360", "--script", "res://scripts/shot_frame_capture.gd"],
            runner,
        )
        frames = (
            state / "family_movie_frames" / "EP_FAMILY_PREVIEW"
        )
        count = len(list(frames.glob("frame_*.png")))
        if count != seconds * fps:
            raise PrivateMovieError("Private movie frame count mismatch")
        voice_file = None
        clip = source.get("voice_clips", {}).get("0")
        if clip is not None:
            # Read only the exact owner/film/hash saved before parent approval.
            # Its bytes are copied into this 0700 temporary render sandbox.
            raw_voice = read_private_shot_voice(
                Path(db_path).absolute().parent / "voice-clips",
                owner=owner, film_id=film_id, clip=clip,
            )
            suffix = voice_path_relative(
                owner=owner, film_id=film_id, shot_index=0,
                media_type=clip["media_type"],
            ).suffix
            voice_file = sandbox / ("private-shot-00" + suffix)
            voice_file.write_bytes(raw_voice)
            voice_file.chmod(0o600)
        staging = sandbox / "private-film.mp4"
        # Film music is chosen only from the pinned CC0 catalog, through
        # source generated from an owner-scoped, currently approved draft.
        # The source has no music field for legacy silent films.
        music_id = str(source.get("director_choices", {}).get("music_id", "none"))
        try:
            ffmpeg_args = private_movie_ffmpeg_args(
                project_root=sandbox,
                frames_pattern=frames / "frame_%05d.png",
                destination=staging, music_id=music_id, fps=fps,
                duration_seconds=seconds, ffmpeg=ffmpeg,
                voice_file=voice_file,
            )
        except FamilyMusicMixError as exc:
            raise PrivateMovieError("Selected packaged background music is unavailable") from exc
        _run_checked(ffmpeg_args, runner)
        if not staging.is_file() or staging.stat().st_size <= 256:
            raise PrivateMovieError("Encoded private MP4 is missing")
        if b"ftyp" not in staging.read_bytes()[:32]:
            raise PrivateMovieError("Encoded output is not an MP4")
        result = _run_checked(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(staging)],
            runner,
        )
        try:
            actual_seconds = float(result.stdout.strip())
        except ValueError as exc:
            raise PrivateMovieError("Cannot verify private MP4 length") from exc
        if abs(actual_seconds - seconds) > 0.6:
            raise PrivateMovieError("Private movie duration mismatch")
        # Verify every audio stream, not just a:0. Silent legacy movies must
        # remain silent, and mixed music/voice must produce exactly one AAC track.
        audio_check = _run_checked(
            [ffprobe, "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_name,start_time,duration",
             "-of", "json", str(staging)], runner,
        )
        try:
            audio_streams = json.loads(audio_check.stdout)["streams"]
            expected_audio = music_id != "none" or voice_file is not None
            if expected_audio:
                if len(audio_streams) != 1 or audio_streams[0]["codec_name"] != "aac":
                    raise ValueError("AAC stream count mismatch")
                audio = audio_streams[0]
                if abs(float(audio["start_time"])) > 0.06:
                    raise ValueError("Audio start mismatch")
                if abs(float(audio["duration"]) - seconds) > 0.6:
                    raise ValueError("Audio duration mismatch")
            elif audio_streams:
                raise ValueError("Legacy silent movie unexpectedly has audio")
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise PrivateMovieError("Private MP4 audio verification failed") from exc
        if staging.stat().st_size > MAX_PRIVATE_MP4_BYTES:
            raise PrivateMovieError("Private MP4 exceeds the 32 MiB download limit")

        # Rendering is slow: an adult may revoke approval, the child may
        # re-edit the film, or an owned Hero may change while Godot runs.
        # Re-open SQLite after encoding and fail closed BEFORE publishing any
        # completed bytes. No long-running subprocess retains an approval.
        latest = SQLiteStudioRepository(Path(db_path))
        fresh_review = current_review_state(
            latest, owner=owner, film_id=film_id
        )
        fresh_source = build_family_film_render_source(
            latest, owner=owner, film_id=film_id
        )
        if (
            fresh_review is None
            or not fresh_review["approved_for_private_render"]
            or fresh_source is None
            or fresh_source != reviewed_source
            or fresh_review["revision"] != source["source_revision"]
        ):
            raise PrivateMovieError(
                "Film or parent approval changed during rendering; no movie saved"
            )

        # Exclusive creation: existing files are never overwritten. No child
        # media is kept in source checkout or Github Actions artifacts.
        created_output = False
        try:
            with output.open("xb") as dest:
                created_output = True
                with staging.open("rb") as video:
                    shutil.copyfileobj(video, dest)
            output.chmod(0o600)
        except Exception:
            if created_output:
                output.unlink(missing_ok=True)
            raise

    return {
        "film_id": film_id,
        "source_revision": source["source_revision"],
        "duration_seconds": seconds,
        "fps": fps,
        "bytes": output.stat().st_size,
        "private_path": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Adult-operated private movie export")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--godot-project", type=Path, required=True)
    parser.add_argument("--film-id", required=True)
    parser.add_argument("--owner", choices=["child_a", "child_b"], required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument(
        "--store-root", type=Path,
        help="Private owner-scoped media root used by Family API downloads",
    )
    parser.add_argument("--fps", type=int, default=6, choices=[2, 6, 12])
    parser.add_argument("--godot-bin", default="godot")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    parser.add_argument("--ffprobe-bin", default="ffprobe")
    parser.add_argument("--xvfb-run-bin", default="xvfb-run")
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        parser.error("Never run a private child export in public GitHub Actions")
    try:
        output_path = args.output
        if args.store_root is not None:
            fp = approved_fingerprint(
                SQLiteStudioRepository(args.db), args.owner, args.film_id
            )
            if fp is None:
                raise PrivateMovieError("Parent approval is required for this film")
            output_path = media_path(
                args.store_root, owner=args.owner, film_id=args.film_id,
                fingerprint=fp, create_dirs=True,
            )
        result = render_private_movie(
            db_path=args.db, project_dir=args.godot_project,
            film_id=args.film_id, owner=args.owner, output_path=output_path,
            godot=args.godot_bin, ffmpeg=args.ffmpeg_bin,
            ffprobe=args.ffprobe_bin, xvfb_run=args.xvfb_run_bin,
            fps=args.fps,
        )
    except (PrivateMovieError, PrivateMovieMediaError) as exc:
        parser.error(str(exc))
    print("Saved private MP4:", result["private_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
