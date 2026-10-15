"""Private 10-second shot-voice metadata/filename policy for W2-02a.

No child audio, token, or filename is accepted by this module. Future upload
endpoints must prove ownership using their existing child-scoped session and
probe the actual binary with FFprobe before applying these checks.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

MAX_VOICE_SECONDS = 10.0
MAX_VOICE_BYTES = 1_500_000
MAX_SHOT_INDEX = 7
ALLOWED_AUDIO_FORMATS = {
    "audio/mp4": ("aac", ".m4a"),
    "audio/webm": ("opus", ".webm"),
    "audio/wav": ("pcm_s16le", ".wav"),
}
FILM_ID = re.compile(r"^FILM_[A-Za-z0-9_-]{3,96}$")


class PrivateVoicePolicyError(ValueError):
    """Unsupported or overlong child-recording candidate; safe for logs."""


def voice_path_relative(
    *,
    owner: str,
    film_id: str,
    shot_index: int,
    media_type: str,
) -> Path:
    """Return only a bounded path *relative* to an adult-owned private root."""
    if owner not in ("child_a", "child_b"):
        raise PrivateVoicePolicyError("Unsupported child profile")
    if not FILM_ID.fullmatch(film_id):
        raise PrivateVoicePolicyError("Invalid private film ID")
    if type(shot_index) is not int or not (0 <= shot_index <= MAX_SHOT_INDEX):
        raise PrivateVoicePolicyError("Invalid shot index")
    if media_type not in ALLOWED_AUDIO_FORMATS:
        raise PrivateVoicePolicyError("Unsupported child voice format")
    extension = ALLOWED_AUDIO_FORMATS[media_type][1]
    return Path(owner) / film_id / f"shot_{shot_index:02d}{extension}"


def validate_probed_voice(
    *,
    media_type: str,
    byte_count: int,
    probe: dict,
) -> float:
    """Check server-side FFprobe JSON, never client-authored duration metadata.

    Caller must verify the probe was produced by the actual uploaded bytes
    and that all files reside under private 0700 paths before saving.
    """
    if media_type not in ALLOWED_AUDIO_FORMATS:
        raise PrivateVoicePolicyError("Unsupported child voice format")
    if type(byte_count) is not int or not (0 < byte_count <= MAX_VOICE_BYTES):
        raise PrivateVoicePolicyError("Voice exceeds private size limit")
    if not isinstance(probe, dict):
        raise PrivateVoicePolicyError("Missing trusted audio probe")
    streams = probe.get("streams")
    if not isinstance(streams, list) or len(streams) != 1:
        raise PrivateVoicePolicyError("Exactly one audio track is required")
    stream = streams[0]
    if not isinstance(stream, dict):
        raise PrivateVoicePolicyError("Invalid audio stream")
    if stream.get("codec_type") != "audio":
        raise PrivateVoicePolicyError("No private voice stream detected")
    if stream.get("codec_name") != ALLOWED_AUDIO_FORMATS[media_type][0]:
        raise PrivateVoicePolicyError("Unsupported private voice codec")
    channels = stream.get("channels")
    if type(channels) is not int or channels not in (1, 2):
        raise PrivateVoicePolicyError("Voice requires mono or stereo")
    try:
        rate = int(stream.get("sample_rate"))
        fmt = probe.get("format", {})
        duration = float(fmt.get("duration"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise PrivateVoicePolicyError("Unverifiable voice metadata") from exc
    if not (8000 <= rate <= 48000) or not math.isfinite(duration):
        raise PrivateVoicePolicyError("Unverifiable voice sample rate or duration")
    if not (0.0 < duration <= MAX_VOICE_SECONDS + 0.05):
        raise PrivateVoicePolicyError("Voice exceeds ten-second limit")
    return duration
