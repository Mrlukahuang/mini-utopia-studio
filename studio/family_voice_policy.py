"""Ten-second per-shot voice contract and private immutable audio storage.

Real recordings stay outside Git, Web assets and CI. Only a child-scoped
FamilyApplication caller may save, and the adult worker may read after review.
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


class PrivateVoiceRevisionConflict(PrivateVoicePolicyError):
    """The private film changed while the child was recording."""


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


# Current Director template has one continuous 15/30-second shot. Other indexes
# remain reserved until a real multi-shot timeline exists; never invent timings.
def _private_voice_dir(root: Path, owner: str, film_id: str, *, create: bool) -> Path:
    import os
    import stat
    voice_path_relative(owner=owner, film_id=film_id, shot_index=0, media_type="audio/mp4")
    root = Path(root)
    if not root.is_absolute():
        raise PrivateVoicePolicyError("Private voice root must be absolute")
    folders = (root, root / owner, root / owner / film_id)
    for folder in folders:
        if folder.is_symlink():
            raise PrivateVoicePolicyError("Symlinked private voice directory")
        if create:
            folder.mkdir(mode=0o700, exist_ok=True)
        if not folder.is_dir():
            raise PrivateVoicePolicyError("Private voice folder unavailable")
        mode = folder.stat()
        if not stat.S_ISDIR(mode.st_mode) or (
            os.name == "posix" and (mode.st_uid != os.getuid() or mode.st_mode & 0o077)
        ):
            raise PrivateVoicePolicyError("Private voice folder must be owner-only")
    return folders[-1]


def _clip_path(root: Path, owner: str, film_id: str, clip: dict, *, create=False) -> Path:
    import re
    if not isinstance(clip, dict):
        raise PrivateVoicePolicyError("Invalid saved voice metadata")
    sha = clip.get("sha256")
    mime = clip.get("media_type")
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
        raise PrivateVoicePolicyError("Invalid saved voice checksum")
    relative = voice_path_relative(
        owner=owner, film_id=film_id, shot_index=0, media_type=mime
    )
    folder = _private_voice_dir(root, owner, film_id, create=create)
    return folder / (relative.stem + "_" + sha + relative.suffix)


def save_private_shot_voice(
    repository, *, voice_root: Path, owner: str, film_id: str,
    shot_index: int, media_type: str, blob: bytes,
    runner=None, ffprobe: str = "ffprobe",
    expected_revision: str | None = None,
) -> dict:
    """Probe uploaded binary before an immutable 0600 save and film revision bump."""
    import hashlib
    import json
    import subprocess
    import tempfile
    from studio.core.enums import AssetType, ReviewStatus
    from studio.models.asset import now_utc

    if shot_index != 0:
        raise PrivateVoicePolicyError("Current movie has only one shot")
    relative = voice_path_relative(
        owner=owner, film_id=film_id, shot_index=shot_index, media_type=media_type
    )
    asset = repository.get_asset(film_id)
    if (
        asset is None or asset.asset_type != AssetType.FILM
        or asset.status == ReviewStatus.ARCHIVED
        or asset.metadata.get("family_owner") != owner
        or "family_film_draft" not in asset.metadata
    ):
        raise PrivateVoicePolicyError("Owned film not found")
    # The pinned contract is optional for existing one-shot Director clients;
    # future UI may pass its saved revision to reject late/stale recordings.
    # FamilyApplication holds its per-process write lock around this check.
    if expected_revision is not None and str(asset.version) != expected_revision:
        raise PrivateVoiceRevisionConflict("Film revision changed during recording")
    if not isinstance(blob, bytes) or not (0 < len(blob) <= MAX_VOICE_BYTES):
        raise PrivateVoicePolicyError("Voice exceeds private size limit")
    folder = _private_voice_dir(voice_root, owner, film_id, create=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=".voice-probe-", suffix=relative.suffix, dir=folder
    ) as temp:
        temp.write(blob)
        temp.flush()
        try:
            outcome = (runner or subprocess.run)(
                [ffprobe, "-v", "error", "-show_streams", "-show_format",
                 "-of", "json", temp.name],
                check=True, capture_output=True, text=True, timeout=12,
            )
            duration = validate_probed_voice(
                media_type=media_type, byte_count=len(blob),
                probe=json.loads(outcome.stdout),
            )
        except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
            raise PrivateVoicePolicyError("Private voice failed media verification") from exc

    digest = hashlib.sha256(blob).hexdigest()
    clip = {"sha256": digest, "media_type": media_type, "duration": round(duration, 3)}
    dest = _clip_path(voice_root, owner, film_id, clip)
    if dest.is_symlink():
        raise PrivateVoicePolicyError("Symlinked private voice file")
    try:
        with dest.open("xb") as output:
            output.write(blob)
        dest.chmod(0o600)
    except FileExistsError:
        # Repeating the same request is safe. Never overwrite prior recordings.
        if read_private_shot_voice(
            voice_root, owner=owner, film_id=film_id, clip=clip
        ) != blob:
            raise PrivateVoicePolicyError("Existing voice is not verified")

    existing = asset.metadata.get("family_voice_clips", {})
    if isinstance(existing, dict) and existing.get("0") == clip:
        return {"film_id": film_id, "revision": str(asset.version),
                "shot_index": 0, "duration_seconds": clip["duration"]}
    if not isinstance(existing, dict):
        raise PrivateVoicePolicyError("Invalid private film voice metadata")
    asset.metadata["family_voice_clips"] = {**existing, "0": clip}
    asset.version += 1  # Immediately invalidates any old parental approval.
    asset.updated_at = now_utc()
    repository.save_asset(asset)
    return {"film_id": film_id, "revision": str(asset.version),
            "shot_index": 0, "duration_seconds": clip["duration"]}


def read_private_shot_voice(
    voice_root: Path, *, owner: str, film_id: str, clip: dict,
) -> bytes:
    """Trusted renderer verifies the pinned bytes, not a child-supplied path."""
    import hashlib
    import os
    import stat
    path = _clip_path(voice_root, owner, film_id, clip)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_size > MAX_VOICE_BYTES
                or st.st_size <= 0 or (os.name == "posix" and (
                    st.st_uid != os.getuid() or st.st_mode & 0o077
                ))):
                raise PrivateVoicePolicyError("Unsafe private voice file")
            with os.fdopen(fd, "rb", closefd=False) as audio:
                blob = audio.read(MAX_VOICE_BYTES + 1)
        finally:
            os.close(fd)
    except OSError as exc:
        raise PrivateVoicePolicyError("Private voice not available") from exc
    if hashlib.sha256(blob).hexdigest() != clip["sha256"]:
        raise PrivateVoicePolicyError("Private voice checksum mismatch")
    return blob
