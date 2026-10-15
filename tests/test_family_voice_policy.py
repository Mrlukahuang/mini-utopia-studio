"""No real child voice or family secrets: synthetic FFprobe metadata only."""
from pathlib import Path

import pytest

from studio.family_voice_policy import (
    PrivateVoicePolicyError, validate_probed_voice, voice_path_relative,
)


def synthetic_aac(duration="9.98"):
    return {
        "format": {"duration": duration},
        "streams": [
            {"codec_type": "audio", "codec_name": "aac",
             "channels": 1, "sample_rate": "44100"}
        ],
    }


def test_probed_10_second_aac_from_safari_is_accepted():
    assert validate_probed_voice(
        media_type="audio/mp4", byte_count=120_000,
        probe=synthetic_aac("10.00"),
    ) == 10.0
    assert voice_path_relative(
        owner="child_a", film_id="FILM_PRIVATE_ABC",
        shot_index=0, media_type="audio/mp4",
    ) == Path("child_a/FILM_PRIVATE_ABC/shot_00.m4a")


@pytest.mark.parametrize("owner,film,index", [
    ("child_c", "FILM_SAFE001", 0),
    ("child_b", "../FILM_CHILD_A", 0),
    ("child_b", "FILM_SAFE001/../../child_a", 0),
    ("child_b", "FILM_SAFE001", -1),
    ("child_b", "FILM_SAFE001", 8),
    ("child_b", "FILM_SAFE001", True),
])
def test_no_sibling_traversal_or_unbounded_shot_paths(owner, film, index):
    with pytest.raises(PrivateVoicePolicyError):
        voice_path_relative(
            owner=owner, film_id=film, shot_index=index,
            media_type="audio/mp4",
        )


@pytest.mark.parametrize("duration", ["10.5", "nan", "-1", "0", "inf", "100"])
def test_long_or_unverifiable_voice_is_rejected(duration):
    with pytest.raises(PrivateVoicePolicyError):
        validate_probed_voice(
            media_type="audio/mp4", byte_count=120_000,
            probe=synthetic_aac(duration),
        )


def test_codec_must_match_container_no_video_or_multiple_streams():
    for codec in ("pcm_s16le", "flac", "mp3", "opus"):
        source = synthetic_aac()
        source["streams"][0]["codec_name"] = codec
        with pytest.raises(PrivateVoicePolicyError):
            validate_probed_voice(
                media_type="audio/mp4", byte_count=120_000,
                probe=source,
            )
    for streams in ([], [synthetic_aac()["streams"][0]] * 2,
                    [{"codec_type": "video", "codec_name": "h264"}]):
        with pytest.raises(PrivateVoicePolicyError):
            validate_probed_voice(
                media_type="audio/mp4", byte_count=120_000,
                probe={"format": {"duration": 1}, "streams": streams},
            )


@pytest.mark.parametrize("mime,size", [
    ("video/mp4", 50), ("audio/mp3", 100),
    ("audio/mp4", 0), ("audio/mp4", -1),
    ("audio/mp4", 1_500_001), ("audio/mp4", True),
])
def test_no_unsafe_format_or_oversized_private_voice(mime, size):
    with pytest.raises(PrivateVoicePolicyError):
        validate_probed_voice(
            media_type=mime, byte_count=size, probe=synthetic_aac(),
        )


def test_opus_and_uncompressed_wav_are_strictly_codec_bound():
    for mime, codec in (("audio/webm", "opus"), ("audio/wav", "pcm_s16le")):
        x = synthetic_aac()
        x["streams"][0]["codec_name"] = codec
        assert validate_probed_voice(
            media_type=mime, byte_count=100_000, probe=x,
        ) > 0
