"""Synthetic FFmpeg command safety for W2-01c; no child recordings."""
from __future__ import annotations

import shutil
import subprocess
import struct
import zlib
from pathlib import Path

import pytest

from studio.family_music_mix import (
    FamilyMusicMixError, private_movie_ffmpeg_args,
)

ROOT = Path(__file__).resolve().parents[1]


def command(choice="sunny_meadow", **params):
    return private_movie_ffmpeg_args(
        project_root=ROOT,
        frames_pattern=Path("/tmp/synthetic_frames/frame_%05d.png"),
        destination=Path("/tmp/parent-private/film.mp4"),
        music_id=choice, fps=params.get("fps", 2),
        duration_seconds=params.get("duration_seconds", 15),
    )


def test_catalog_only_adds_pinned_wav_as_aac_input():
    for choice in ("sunny_meadow", "cloud_parade", "moonlit_garden"):
        argv = command(choice)
        assert argv[0] == "ffmpeg"
        assert "-stream_loop" in argv
        assert "-c:a" in argv and argv[argv.index("-c:a") + 1] == "aac"
        assert "-map" in argv and "1:a:0" in argv
        assert str(ROOT / "godot" / "assets" / "audio" / "cc0_music") in " ".join(argv)
        assert argv[-1] == "/tmp/parent-private/film.mp4"
        assert "-filter_complex_script" not in argv

    silent = command("none")
    assert "-stream_loop" not in silent
    assert "-c:a" not in silent
    assert "-map" not in silent


@pytest.mark.parametrize("bad", [
    "../private/child.wav", "/etc/passwd", "https://example.com/a.wav",
    "Sunny Meadow", "", "sibling's film",
])
def test_music_selection_cannot_escape_catalog(bad):
    with pytest.raises(FamilyMusicMixError):
        command(bad)


@pytest.mark.parametrize("fps,seconds", [(0, 15), (30, 15), (2, 11), (2, 31)])
def test_music_render_must_be_approved_duration_and_fps(fps, seconds):
    with pytest.raises(FamilyMusicMixError):
        command("none", fps=fps, duration_seconds=seconds)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(
        ">I", zlib.crc32(kind + data) & 0xffffffff
    )


def _minimal_synthetic_png() -> bytes:
    width, height = 64, 64
    row = b"\x00" + b"\xb9\xe7\xd0" * width
    pixels = zlib.compress(row * height, level=5)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", pixels)
        + _png_chunk(b"IEND", b"")
    )


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="Host lacks FFmpeg; exact argv safety remains separately tested",
)
def test_real_synthetic_mp4_has_aac_music_without_voices(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    pix = _minimal_synthetic_png()
    for i in range(30):
        (frames / f"frame_{i:05d}.png").write_bytes(pix)
    output = tmp_path / "synthetic.mp4"
    argv = private_movie_ffmpeg_args(
        project_root=ROOT,
        frames_pattern=frames / "frame_%05d.png",
        destination=output,
        music_id="cloud_parade",
        fps=2, duration_seconds=15,
    )
    subprocess.run(argv, check=True, capture_output=True, timeout=90)
    assert output.is_file() and output.stat().st_size > 256
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name",
         "-of", "default=noprint_wrappers=1", str(output)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    assert "codec_name=aac" in result.stdout
    assert "codec_type=video" in result.stdout
    assert "codec_type=audio" in result.stdout


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="Real FFmpeg/ffprobe required for synthetic audio mix",
)
@pytest.mark.parametrize("seconds", [15, 30])
def test_real_synthetic_music_and_voice_mix_single_aac(seconds, tmp_path):
    """Real encoder mix of packaged CC0 music and generated non-child voice tone."""
    import json
    import math
    import wave

    frames = tmp_path / "frames"
    frames.mkdir()
    pixel = _minimal_synthetic_png()
    for i in range(seconds * 2):
        (frames / f"frame_{i:05d}.png").write_bytes(pixel)
    voice = tmp_path / "synthetic_voice.wav"
    rate = 8000
    with wave.open(str(voice), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        # Two seconds of deliberately generated tone, not a child's recording.
        wav.writeframes(b"".join(
            struct.pack("<h", int(5000 * math.sin(2 * math.pi * 440 * n / rate)))
            for n in range(rate * 2)
        ))
    output = tmp_path / "mixed.mp4"
    argv = private_movie_ffmpeg_args(
        project_root=ROOT, frames_pattern=frames / "frame_%05d.png",
        destination=output, music_id="sunny_meadow",
        voice_file=voice, fps=2, duration_seconds=seconds,
    )
    assert "amix=" in " ".join(argv)
    subprocess.run(argv, check=True, capture_output=True, timeout=120)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_name,start_time,duration",
         "-of", "json", str(output)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert len(streams) == 1 and streams[0]["codec_name"] == "aac"
    assert abs(float(streams[0]["start_time"])) <= 0.06
    assert abs(float(streams[0]["duration"]) - seconds) <= 0.6
