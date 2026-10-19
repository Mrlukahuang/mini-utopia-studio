"""W2-01c synthetic media acceptance, no private family content."""
from __future__ import annotations

import shutil
import pytest

@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
def test_offline_ffmpeg_available():
    assert shutil.which("ffmpeg")
    assert shutil.which("ffprobe")
