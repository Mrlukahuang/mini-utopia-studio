#!/usr/bin/env python3
"""Prepare the real KayKit Mountain Town world kit from local source ZIPs.

One command:
    python3 tools/prepare_mountain_town_assets.py

The script:
- finds the already-downloaded KayKit ZIPs
- extracts only the versioned world-kit assets + direct glTF dependencies
- preserves all source archives
- bakes Candidate B variants for Medieval + Forest assets
- leaves Resource Bits in their source neutral/material colors
- writes a local ignored installed manifest for Godot
"""

from __future__ import annotations

import argparse
import colorsys
import json
import posixpath
import shutil
import statistics
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
GODOT_ROOT = REPO_ROOT / "godot"
CATALOG_PATH = REPO_ROOT / "assets" / "catalogs" / "mountain_town_world_kit_v1.json"
INSTALL_ROOT = GODOT_ROOT / "assets" / "external" / "worldkit"
PALETTE_PATH = GODOT_ROOT / "config" / "style" / "core_palette_candidates_v0_9.json"
PROFILE_PATH = GODOT_ROOT / "config" / "style" / "profiles" / "core_candidate_b_v0_1.json"
ATLAS_MAPS = {
    "kaykit_forest": REPO_ROOT / "assets" / "catalogs" / "atlas_maps" / "kaykit_forest_v0_1.json",
    "kaykit_medieval": REPO_ROOT / "assets" / "catalogs" / "atlas_maps" / "kaykit_medieval_v0_1.json",
}
GREEN_TERRAIN_MAP = (
    REPO_ROOT
    / "assets"
    / "catalogs"
    / "atlas_maps"
    / "kaykit_medieval_green_terrain_v0_1.json"
)
CORE_PROFILE_ID = "core_candidate_b"
GREEN_TERRAIN_PROFILE_ID = "core_candidate_b_green_terrain"


def candidate_dirs(extra: list[Path]) -> list[Path]:
    home = Path.home()
    raw = [
        *extra,
        Path.cwd(),
        REPO_ROOT,
        REPO_ROOT.parent,
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
    ]
    result: list[Path] = []
    seen: set[Path] = set()
    for item in raw:
        try:
            item = item.expanduser().resolve()
        except OSError:
            continue
        if item.exists() and item.is_dir() and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def find_archive(names: list[str], dirs: list[Path]) -> Path | None:
    for directory in dirs:
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def safe_member(member: str) -> str:
    normalized = posixpath.normpath(member).lstrip("/")
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"unsafe zip member: {member}")
    return normalized


def copy_member(zf: zipfile.ZipFile, member: str, destination: Path) -> None:
    member = safe_member(member)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def is_external_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    return bool(parsed.scheme) or uri.startswith("data:")


def install_asset(zf: zipfile.ZipFile, entry: dict) -> dict:
    source_member = safe_member(entry["source_member"])
    destination_dir = INSTALL_ROOT / entry["id"]
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_file = destination_dir / Path(source_member).name
    copy_member(zf, source_member, destination_file)

    copied = [destination_file]
    if destination_file.suffix.lower() == ".gltf":
        data = json.loads(zf.read(source_member))
        source_base = posixpath.dirname(source_member)
        uris: list[str] = []
        for buffer in data.get("buffers", []):
            if buffer.get("uri"):
                uris.append(buffer["uri"])
        for image in data.get("images", []):
            if image.get("uri"):
                uris.append(image["uri"])

        for uri in sorted(set(uris)):
            if is_external_uri(uri):
                continue
            source_dep = safe_member(posixpath.join(source_base, uri))
            destination_dep = destination_dir / Path(uri)
            copy_member(zf, source_dep, destination_dep)
            copied.append(destination_dep)

    installed = dict(entry)
    installed["res_path"] = "res://" + destination_file.relative_to(GODOT_ROOT).as_posix()
    installed["installed_files"] = [
        path.relative_to(GODOT_ROOT).as_posix() for path in copied
    ]
    return installed


def hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def semantic_colors() -> dict[str, str]:
    palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))["colors"]
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return {
        slot: palette[palette_key]
        for slot, palette_key in profile["slot_to_palette_key"].items()
    }


def region_bounds(width: int, height: int, mapping: dict):
    layout = mapping["layout"]
    if layout["type"] == "horizontal_bands":
        bands = int(layout["bands"])
        for item in mapping["regions"]:
            band = int(item["band"])
            yield (
                0,
                round(height * band / bands),
                width,
                round(height * (band + 1) / bands),
            ), item["slot"]
        return

    rows = int(layout["rows"])
    columns = int(layout["columns"])
    for row in range(rows):
        y0 = round(height * row / rows)
        y1 = round(height * (row + 1) / rows)
        for column in range(columns):
            x0 = round(width * column / columns)
            x1 = round(width * (column + 1) / columns)
            yield (x0, y0, x1, y1), mapping["regions"][row][column]


def pixel_lightness(pixel) -> float:
    r, g, b = (channel / 255.0 for channel in pixel[:3])
    return colorsys.rgb_to_hls(r, g, b)[1]


def recolor_region(image: Image.Image, bounds, target_hex: str) -> None:
    x0, y0, x1, y1 = bounds
    target = hex_rgb(target_hex)
    target_h, target_l, target_s = colorsys.rgb_to_hls(*target)
    pixels = image.load()

    lightness_samples: list[float] = []
    sx = max(1, (x1 - x0) // 48)
    sy = max(1, (y1 - y0) // 48)
    for y in range(y0, y1, sy):
        for x in range(x0, x1, sx):
            lightness_samples.append(pixel_lightness(pixels[x, y]))
    source_center = statistics.median(lightness_samples) if lightness_samples else 0.5

    for y in range(y0, y1):
        for x in range(x0, x1):
            source_l = pixel_lightness(pixels[x, y])
            new_l = target_l + (source_l - source_center) * 0.82
            new_l = max(0.07, min(0.91, new_l))
            r, g, b = colorsys.hls_to_rgb(target_h, new_l, target_s)
            alpha = pixels[x, y][3]
            pixels[x, y] = (
                round(r * 255),
                round(g * 255),
                round(b * 255),
                alpha,
            )


def bake_profile(
    entry: dict,
    mapping: dict,
    colors: dict[str, str],
    profile_id: str,
) -> str:
    source = GODOT_ROOT / entry["res_path"].removeprefix("res://")
    if source.suffix.lower() != ".gltf":
        return entry["res_path"]

    data = json.loads(source.read_text(encoding="utf-8"))
    derived = source.with_name(f"{source.stem}__{profile_id}{source.suffix}")
    changed = False

    for image_entry in data.get("images", []):
        uri = image_entry.get("uri")
        if not uri or uri.startswith("data:"):
            continue
        texture = source.parent / uri
        if texture.name != mapping["atlas_name"]:
            continue

        derived_texture = texture.with_name(
            f"{texture.stem}__{profile_id}{texture.suffix}"
        )
        image = Image.open(texture).convert("RGBA")
        for bounds, slot in region_bounds(image.width, image.height, mapping):
            recolor_region(image, bounds, colors[slot])
        image.save(derived_texture)
        image_entry["uri"] = derived_texture.name
        changed = True

    if not changed:
        return entry["res_path"]

    derived.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "res://" + derived.relative_to(GODOT_ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", action="append", default=[])
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if args.clean and INSTALL_ROOT.exists():
        shutil.rmtree(INSTALL_ROOT)
    INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
    licenses = INSTALL_ROOT / "_licenses"
    licenses.mkdir(exist_ok=True)

    dirs = candidate_dirs([Path(value) for value in args.source_dir])
    archives: dict[str, Path] = {}
    missing: list[tuple[str, list[str]]] = []
    for pack_id, pack in catalog["packs"].items():
        archive = find_archive(pack["archive_candidates"], dirs)
        if archive is None:
            missing.append((pack_id, pack["archive_candidates"]))
        else:
            archives[pack_id] = archive

    if missing:
        print("Missing source ZIPs:")
        for pack_id, names in missing:
            print(f"  - {pack_id}: {' or '.join(names)}")
        print("\nSearched:")
        for directory in dirs:
            print(f"  - {directory}")
        return 2

    installed: list[dict] = []
    for pack_id, archive in archives.items():
        pack = catalog["packs"][pack_id]
        with zipfile.ZipFile(archive) as zf:
            if pack.get("license_member"):
                copy_member(
                    zf,
                    pack["license_member"],
                    licenses / f"{pack_id}.txt",
                )
            for entry in catalog["assets"]:
                if entry["pack"] != pack_id:
                    continue
                result = install_asset(zf, entry)
                result["source_archive"] = archive.name
                installed.append(result)
                print(f"Installed {entry['id']}")

    colors = semantic_colors()
    mappings = {
        pack_id: json.loads(path.read_text(encoding="utf-8"))
        for pack_id, path in ATLAS_MAPS.items()
    }
    green_terrain_mapping = json.loads(
        GREEN_TERRAIN_MAP.read_text(encoding="utf-8")
    )

    core_baked = 0
    green_terrain_baked = 0
    green_categories = {"terrain", "road", "river", "nature"}

    for entry in installed:
        pack_id = entry["pack"]
        if pack_id in mappings:
            derived = bake_profile(
                entry,
                mappings[pack_id],
                colors,
                CORE_PROFILE_ID,
            )
            entry.setdefault("profile_res_paths", {})[CORE_PROFILE_ID] = derived
            core_baked += 1
            print(f"Baked {entry['id']} -> {CORE_PROFILE_ID}")

        if (
            pack_id == "kaykit_medieval"
            and entry.get("category") in green_categories
        ):
            terrain_derived = bake_profile(
                entry,
                green_terrain_mapping,
                colors,
                GREEN_TERRAIN_PROFILE_ID,
            )
            entry.setdefault("profile_res_paths", {})[
                GREEN_TERRAIN_PROFILE_ID
            ] = terrain_derived
            green_terrain_baked += 1
            print(
                f"Baked {entry['id']} -> {GREEN_TERRAIN_PROFILE_ID}"
            )

    manifest = {
        "schema_version": "1.0",
        "source_catalog": "assets/catalogs/mountain_town_world_kit_v1.json",
        "count": len(installed),
        "palette_profiles": {
            CORE_PROFILE_ID: {"baked_count": core_baked},
            GREEN_TERRAIN_PROFILE_ID: {
                "baked_count": green_terrain_baked,
                "categories": sorted(green_categories),
            },
        },
        "assets": installed,
    }
    (INSTALL_ROOT / "installed_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nPrepared {len(installed)} Mountain Town assets.")
    print(f"Candidate-B baked assets: {core_baked}.")
    print(
        "Green-terrain baked assets: "
        f"{green_terrain_baked} ({GREEN_TERRAIN_PROFILE_ID})."
    )
    print(f"Godot destination: {INSTALL_ROOT}")
    print("Return to Godot, let Import finish, then run the Mountain Town scene.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
