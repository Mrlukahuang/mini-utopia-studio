"""Whitelisted, original CC0 Mini Utopia background music (V1-W2-01a).

No family-supplied path ever reaches the filesystem: directors save *IDs* only.
"""
from __future__ import annotations

from pathlib import Path

MUSIC_BASE = Path("godot/assets/audio/cc0_music")
MUSIC_TRACKS: dict[str, dict[str, str | float]] = {
    "sunny_meadow": {"title": "Sunny Meadow", "filename": "sunny_meadow.wav", "duration_seconds": 17.78},
    "cloud_parade": {"title": "Cloud Parade", "filename": "cloud_parade.wav", "duration_seconds": 16},
    "moonlit_garden": {"title": "Moonlit Garden", "filename": "moonlit_garden.wav", "duration_seconds": 22.33},
}
MUSIC_CHOICES = ("none", *MUSIC_TRACKS)


def music_file(project_root: Path, music_id: str) -> Path | None:
    """Return an internal pinned WAV path; never take a URL/path from a child."""
    if music_id == "none":
        return None
    track = MUSIC_TRACKS.get(music_id)
    if track is None:
        raise ValueError("Unknown private film background music ID")
    return project_root / MUSIC_BASE / str(track["filename"])
