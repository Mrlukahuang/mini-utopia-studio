"""Bounded FFmpeg inputs for family background music (V1-W2-01c).

This module builds *only* argument vectors. An adult-approved private worker
executes them later, never with a shell and never with a client-provided path.
"""
from __future__ import annotations

from pathlib import Path

from studio.family_music_catalog import MUSIC_BASE, music_file


class FamilyMusicMixError(ValueError):
    """Invalid finite render parameters or packaged CC0 music selection."""


def private_movie_ffmpeg_args(
    *,
    project_root: Path,
    frames_pattern: Path,
    destination: Path,
    music_id: str,
    fps: int,
    duration_seconds: int,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    """Prepare an AAC/music or silent MP4 command using the exact pinned WAV.

    Only the catalog maps an ID to an asset. The caller must separately verify
    the saved film's owner, current parent approval, output permissions and
    continued approval before publishing the final MP4.
    """
    if fps not in (2, 6, 12) or duration_seconds not in (15, 30):
        raise FamilyMusicMixError("Invalid family movie duration or fps")

    project = Path(project_root).resolve()
    try:
        selected = music_file(project, music_id)
    except (ValueError, TypeError) as exc:
        raise FamilyMusicMixError("Unknown background music ID") from exc

    command = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
        "-y", "-framerate", str(fps), "-i", str(frames_pattern),
    ]
    if selected is not None:
        # Enforce a resolved, fixed pack path. No child-supplied filesystem
        # value, URL/protocol, or directory traversal becomes an ffmpeg input.
        allowed_root = (project / MUSIC_BASE).resolve()
        track = selected.resolve(strict=False)
        if (
            not track.is_file()
            or track.suffix.lower() != ".wav"
            or not track.is_relative_to(allowed_root)
        ):
            raise FamilyMusicMixError("Packaged CC0 music file missing")
        command.extend([
            "-stream_loop", "-1", "-i", str(track),
            "-map", "0:v:0", "-map", "1:a:0",
        ])
    command.extend([
        "-t", str(duration_seconds),
        "-c:v", "libx264", "-threads", "2", "-preset", "ultrafast",
        "-crf", "28", "-pix_fmt", "yuv420p",
    ])
    if selected is not None:
        command.extend(["-c:a", "aac", "-b:a", "128k"])
    command.extend(["-movflags", "+faststart", str(destination)])
    return command
