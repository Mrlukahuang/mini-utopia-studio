#!/usr/bin/env python3
"""Bake Mini Utopia palette-profile variants for locally installed Golden glTF assets.

Source ZIPs and source-installed glTF/PNG files are never modified. The tool writes
new derived textures + glTF files beside the local Golden copies and records
profile-specific res:// paths in installed_manifest.json.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import statistics
from pathlib import Path
from typing import Iterable

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
GODOT_ROOT = REPO_ROOT / "godot"
INSTALLED_MANIFEST = GODOT_ROOT / "assets" / "external" / "golden" / "installed_manifest.json"
PALETTE_PATH = GODOT_ROOT / "config" / "style" / "core_palette_candidates_v0_9.json"
PROFILE_DIR = GODOT_ROOT / "config" / "style" / "profiles"
ATLAS_MAP_DIR = REPO_ROOT / "assets" / "catalogs" / "atlas_maps"

PACK_MAP_FILES = {
    "kaykit_forest": "kaykit_forest_v0_1.json",
    "kaykit_medieval": "kaykit_medieval_v0_1.json",
}


def _hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _profile_path(profile_id: str) -> Path:
    candidates = sorted(PROFILE_DIR.glob(f"{profile_id}*.json"))
    if not candidates:
        raise FileNotFoundError(f"No palette profile found for {profile_id!r} in {PROFILE_DIR}")
    return candidates[0]


def _resolve_semantic_colors(profile_id: str) -> dict[str, str]:
    palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
    profile = json.loads(_profile_path(profile_id).read_text(encoding="utf-8"))
    colors = palette["colors"]
    resolved: dict[str, str] = {}
    for slot, palette_key in profile["slot_to_palette_key"].items():
        resolved[slot] = colors[palette_key]
    return resolved


def _region_bounds(width: int, height: int, mapping: dict) -> list[tuple[tuple[int, int, int, int], str]]:
    layout = mapping["layout"]
    regions: list[tuple[tuple[int, int, int, int], str]] = []

    if layout["type"] == "horizontal_bands":
        bands = int(layout["bands"])
        for item in mapping["regions"]:
            band = int(item["band"])
            y0 = round(height * band / bands)
            y1 = round(height * (band + 1) / bands)
            regions.append(((0, y0, width, y1), item["slot"]))
        return regions

    if layout["type"] == "grid":
        rows = int(layout["rows"])
        columns = int(layout["columns"])
        slot_rows = mapping["regions"]
        if len(slot_rows) != rows or any(len(row) != columns for row in slot_rows):
            raise ValueError("grid mapping dimensions do not match regions")
        for row in range(rows):
            y0 = round(height * row / rows)
            y1 = round(height * (row + 1) / rows)
            for column in range(columns):
                x0 = round(width * column / columns)
                x1 = round(width * (column + 1) / columns)
                regions.append(((x0, y0, x1, y1), slot_rows[row][column]))
        return regions

    raise ValueError(f"Unsupported atlas layout: {layout['type']}")


def _lightness(rgb: tuple[int, int, int, int]) -> float:
    r, g, b = (channel / 255.0 for channel in rgb[:3])
    return colorsys.rgb_to_hls(r, g, b)[1]


def _recolor_region(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    target_hex: str,
    gradient_strength: float,
) -> None:
    x0, y0, x1, y1 = bounds
    target_r, target_g, target_b = _hex_rgb(target_hex)
    target_h, target_l, target_s = colorsys.rgb_to_hls(target_r, target_g, target_b)

    pixels = image.load()
    sampled_lightness: list[float] = []
    sample_step_x = max(1, (x1 - x0) // 64)
    sample_step_y = max(1, (y1 - y0) // 64)
    for y in range(y0, y1, sample_step_y):
        for x in range(x0, x1, sample_step_x):
            sampled_lightness.append(_lightness(pixels[x, y]))

    source_center = statistics.median(sampled_lightness) if sampled_lightness else 0.5

    for y in range(y0, y1):
        for x in range(x0, x1):
            source = pixels[x, y]
            source_l = _lightness(source)
            new_l = target_l + (source_l - source_center) * gradient_strength
            new_l = max(0.07, min(0.91, new_l))
            r, g, b = colorsys.hls_to_rgb(target_h, new_l, target_s)
            pixels[x, y] = (
                round(r * 255),
                round(g * 255),
                round(b * 255),
                source[3],
            )


def _bake_texture(source: Path, destination: Path, mapping: dict, semantic_colors: dict[str, str]) -> None:
    image = Image.open(source).convert("RGBA")
    for bounds, slot in _region_bounds(image.width, image.height, mapping):
        target = semantic_colors[slot]
        _recolor_region(image, bounds, target, gradient_strength=0.82)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def _derived_name(source: Path, profile_id: str) -> Path:
    return source.with_name(f"{source.stem}__{profile_id}{source.suffix}")


def _res_to_path(res_path: str) -> Path:
    if not res_path.startswith("res://"):
        raise ValueError(f"Expected res:// path, got {res_path}")
    return GODOT_ROOT / res_path.removeprefix("res://")


def _path_to_res(path: Path) -> str:
    return "res://" + path.relative_to(GODOT_ROOT).as_posix()


def _bake_anchor(entry: dict, profile_id: str, mapping: dict, semantic_colors: dict[str, str]) -> str:
    source_gltf = _res_to_path(entry["res_path"])
    if source_gltf.suffix.lower() != ".gltf":
        raise ValueError(f"First atlas-remap pass expects glTF, got {source_gltf}")

    data = json.loads(source_gltf.read_text(encoding="utf-8"))
    derived_gltf = _derived_name(source_gltf, profile_id)

    for image_entry in data.get("images", []):
        uri = image_entry.get("uri")
        if not uri or uri.startswith("data:"):
            continue
        source_texture = source_gltf.parent / uri
        if source_texture.name != mapping["atlas_name"]:
            continue
        derived_texture = _derived_name(source_texture, profile_id)
        _bake_texture(source_texture, derived_texture, mapping, semantic_colors)
        image_entry["uri"] = derived_texture.name

    derived_gltf.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return _path_to_res(derived_gltf)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="core_candidate_b")
    parser.add_argument(
        "--packs",
        nargs="*",
        default=["kaykit_forest", "kaykit_medieval"],
        choices=sorted(PACK_MAP_FILES),
    )
    args = parser.parse_args()

    if not INSTALLED_MANIFEST.exists():
        raise SystemExit(
            "Golden anchors are not installed. Run: python3 tools/install_golden_anchors.py"
        )

    installed = json.loads(INSTALLED_MANIFEST.read_text(encoding="utf-8"))
    semantic_colors = _resolve_semantic_colors(args.profile)

    mappings = {
        pack: json.loads((ATLAS_MAP_DIR / PACK_MAP_FILES[pack]).read_text(encoding="utf-8"))
        for pack in args.packs
    }

    baked = 0
    for entry in installed.get("anchors", []):
        pack = entry.get("pack")
        if pack not in mappings:
            continue
        derived_res = _bake_anchor(
            entry,
            args.profile,
            mappings[pack],
            semantic_colors,
        )
        entry.setdefault("profile_res_paths", {})[args.profile] = derived_res
        baked += 1
        print(f"Baked {entry['id']} -> {args.profile}")

    installed.setdefault("palette_profiles", {})[args.profile] = {
        "packs": list(args.packs),
        "derived_anchor_count": baked,
    }
    INSTALLED_MANIFEST.write_text(json.dumps(installed, indent=2) + "\n", encoding="utf-8")

    print(f"\nBaked {baked} derived Golden assets for {args.profile}.")
    print("Source glTF/PNG files were not modified.")
    print("Return to Godot and let it import the new derived resources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
