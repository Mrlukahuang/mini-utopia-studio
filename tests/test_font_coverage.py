"""Validate actual font cmap for all Hanzi in game source and GB2312 level 1."""
from pathlib import Path
import re

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "godot" / "assets" / "fonts"
RESOURCE = FONT_DIR / "NotoSansSC-UI.tres"


def _gb2312_level_one():
    # 16..55 rows, with 55th truncated after 89 cells: 3755 codepoints.
    chars = set()
    for first in range(0xB0, 0xD8):
        for second in range(0xA1, 0xFF if first < 0xD7 else 0xFA):
            chars.add(ord(bytes((first, second)).decode("gb2312")))
    assert len(chars) == 3755
    return chars


def _configured_hanzi_cmap():
    resource = RESOURCE.read_text(encoding="utf-8")
    paths = re.findall(r'path="res://assets/fonts/([^"]+)"', resource)
    assert paths, "No Noto Sans SC font resources configured"
    covered = set()
    for name in paths:
        font_path = FONT_DIR / name
        assert font_path.is_file(), f"Missing font asset: {name}"
        with TTFont(font_path, lazy=True) as font:
            for table in font["cmap"].tables:
                if table.isUnicode():
                    covered.update(table.cmap)
    return covered


def _hanzi_in_sources():
    found = {}
    for path in (ROOT / "godot").rglob("*"):
        if path.suffix not in (".gd", ".tscn"):
            continue
        for char in set(path.read_text(encoding="utf-8")):
            if (0x3400 <= ord(char) <= 0x9FFF) or (0xF900 <= ord(char) <= 0xFAFF):
                found.setdefault(char, []).append(path.relative_to(ROOT).as_posix())
    return found


def test_gb2312_level_one_coverage():
    covered = _configured_hanzi_cmap()
    required = _gb2312_level_one()
    missing = required - covered
    ratio = (len(required) - len(missing)) / len(required)
    assert ratio == 1.0, (
        f"GB2312 level-one coverage {ratio:.2%} < 100%; "
        f"missing {len(missing)}: {''.join(sorted(map(chr, missing))[:80])}"
    )


def test_all_godot_hanzi_exist_in_configured_font():
    covered = _configured_hanzi_cmap()
    found = _hanzi_in_sources()
    missing = sorted((char for char in found if ord(char) not in covered))
    detail = "; ".join(
        f"{char} ({found[char][0]})" for char in missing[:40]
    )
    assert not missing, f"{len(missing)} Hanzi missing from Noto Sans SC: {detail}"



def test_basic_latin_and_punctuation_are_available():
    covered = _configured_hanzi_cmap()
    required = {ord(ch) for ch in (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789 .,!?;:'\"-+()/"
        "，。！？：；（）《》、“”‘’—…"
    )}
    missing = required - covered
    assert not missing, (
        "Missing basic Latin / punctuation glyphs: "
        + " ".join(f"U+{cp:04X}" for cp in sorted(missing))
    )
