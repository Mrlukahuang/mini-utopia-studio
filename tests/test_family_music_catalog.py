"""Audio asset metadata/license and child-path safety for W2-01a."""
from __future__ import annotations
import struct
import wave
from pathlib import Path
import pytest
from studio.family_music_catalog import MUSIC_CHOICES, MUSIC_TRACKS, music_file

ROOT = Path(__file__).resolve().parents[1]


def test_three_original_cc0_music_tracks_are_embedded():
    assert len(MUSIC_TRACKS) == 3
    assert MUSIC_CHOICES[0] == "none"
    for track_id, spec in MUSIC_TRACKS.items():
        filename = music_file(ROOT, track_id)
        assert filename is not None and filename.is_file()
        with wave.open(str(filename), "rb") as wav:
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
            assert wav.getframerate() == 11025
            assert 15 <= wav.getnframes() / wav.getframerate() <= 24
            frames = wav.readframes(min(11025, wav.getnframes()))
            assert any(v != 0 for v in struct.unpack("<" + "h"*(len(frames)//2), frames))
    license_text = (ROOT / "godot/assets/audio/cc0_music/README.md").read_text()
    assert "CC0 1.0" in license_text and "original" in license_text.lower()


@pytest.mark.parametrize("music_id", ["../secrets", "https://attacker.invalid/a.wav", "/etc/passwd", "", "Sunny Meadow"])
def test_music_id_rejects_arbitrary_paths(music_id):
    with pytest.raises(ValueError):
        music_file(ROOT, music_id)


def test_none_is_silent_and_has_no_file():
    assert music_file(ROOT, "none") is None



def test_music_id_allowed_by_private_film_draft():
    from pydantic import ValidationError
    from studio.family_films import FamilyFilmDraft

    base = {"display_name": "Synthetic short film", "character_id": "CHAR_TEST123"}
    for choice in ("none", "sunny_meadow", "cloud_parade", "moonlit_garden"):
        draft = FamilyFilmDraft.model_validate({**base, "music_id": choice})
        assert draft.music_id == choice
    assert FamilyFilmDraft.model_validate(base).music_id == "none"
    for choice in ("/etc/passwd", "../private/voice.wav", "https://example.org/song.wav"):
        with pytest.raises(ValidationError):
            FamilyFilmDraft.model_validate({**base, "music_id": choice})
