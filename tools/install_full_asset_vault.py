#!/usr/bin/env python3
"""Install the user's complete local 3D asset library into Godot once.

Default behavior scans common local folders for asset ZIPs whose names look like
KayKit, Kenney, Quaternius or MegaKit packs. Every .gltf/.glb asset is installed
with the direct buffer/image dependencies required by glTF.

Extracted third-party files live under:
    godot/assets/external/library/

They are intentionally gitignored. Source ZIPs are never modified.

Examples:
    python3 tools/install_full_asset_vault.py
    python3 tools/install_full_asset_vault.py --source-dir /path/to/packs
    python3 tools/install_full_asset_vault.py --clean
    python3 tools/install_full_asset_vault.py --include-all-3d-zips
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
GODOT_ROOT = REPO_ROOT / "godot"
VAULT_ROOT = GODOT_ROOT / "assets" / "external" / "library"
MANIFEST_PATH = VAULT_ROOT / "asset_vault_manifest.json"
SUPPORTED_EXTENSIONS = {".gltf", ".glb"}
DEFAULT_NAME_HINTS = ("kaykit", "kenney", "quaternius", "megakit")


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


def discover_archives(
    directories: list[Path],
    include_all_3d_zips: bool,
) -> list[Path]:
    # Keep the first archive with a given filename according to directory
    # priority. This avoids importing duplicate downloads into the same pack
    # slug and keeps the one-time vault deterministic.
    found_by_name: dict[str, Path] = {}
    for directory in directories:
        try:
            entries = sorted(directory.glob("*.zip"))
        except OSError:
            continue
        for archive in entries:
            name = archive.name.lower()
            if not (
                include_all_3d_zips
                or any(hint in name for hint in DEFAULT_NAME_HINTS)
            ):
                continue
            found_by_name.setdefault(name, archive.resolve())
    return sorted(
        found_by_name.values(),
        key=lambda p: p.name.lower(),
    )


def safe_member(member: str) -> str:
    normalized = posixpath.normpath(member).lstrip("/")
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"unsafe zip member: {member}")
    return normalized


def is_external_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    return bool(parsed.scheme) or uri.startswith("data:")


def archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    stem = Path(value).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return stem or "asset-pack"


def zip_has_3d_assets(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return any(
                Path(info.filename).suffix.lower() in SUPPORTED_EXTENSIONS
                for info in zf.infolist()
                if not info.is_dir()
            )
    except (OSError, zipfile.BadZipFile):
        return False


def common_top_folder(asset_members: list[str]) -> str | None:
    if not asset_members:
        return None
    first_parts = []
    for member in asset_members:
        parts = safe_member(member).split("/")
        if len(parts) < 2:
            return None
        first_parts.append(parts[0])
    candidate = first_parts[0]
    if all(part == candidate for part in first_parts):
        return candidate
    return None


def relative_member(member: str, common_root: str | None) -> str:
    normalized = safe_member(member)
    if common_root and normalized.startswith(common_root + "/"):
        return normalized[len(common_root) + 1 :]
    return normalized


def copy_member(
    zf: zipfile.ZipFile,
    member: str,
    destination: Path,
) -> None:
    normalized = safe_member(member)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(normalized) as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def gltf_dependency_members(
    zf: zipfile.ZipFile,
    source_member: str,
) -> list[str]:
    try:
        data = json.loads(zf.read(source_member))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return []

    base = posixpath.dirname(source_member)
    uris: set[str] = set()

    for buffer in data.get("buffers", []):
        uri = buffer.get("uri")
        if uri and not is_external_uri(uri):
            uris.add(uri)

    for image in data.get("images", []):
        uri = image.get("uri")
        if uri and not is_external_uri(uri):
            uris.add(uri)

    result = []
    names = set(zf.namelist())
    for uri in sorted(uris):
        dep = safe_member(posixpath.join(base, uri))
        if dep in names:
            result.append(dep)
    return result


def copy_license_files(
    zf: zipfile.ZipFile,
    pack_root: Path,
    common_root: str | None,
) -> list[str]:
    copied: list[str] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        basename = Path(info.filename).name.lower()
        if not (
            "license" in basename
            or basename in {"copying.txt", "copyright.txt"}
        ):
            continue

        rel = relative_member(info.filename, common_root)
        destination = pack_root / "_licenses" / Path(rel).name
        copy_member(zf, info.filename, destination)
        copied.append(
            destination.relative_to(GODOT_ROOT).as_posix()
        )
    return copied


def install_archive(
    archive: Path,
    archive_hash: str,
) -> dict:
    pack_slug = slugify(archive.name)
    pack_root = VAULT_ROOT / pack_slug

    with zipfile.ZipFile(archive) as zf:
        asset_members = [
            safe_member(info.filename)
            for info in zf.infolist()
            if (
                not info.is_dir()
                and Path(info.filename).suffix.lower()
                in SUPPORTED_EXTENSIONS
            )
        ]
        common_root = common_top_folder(asset_members)

        if pack_root.exists():
            shutil.rmtree(pack_root)
        pack_root.mkdir(parents=True, exist_ok=True)

        assets: list[dict] = []
        copied_members: set[str] = set()

        for source_member in sorted(asset_members):
            rel = relative_member(source_member, common_root)
            destination = pack_root / rel
            copy_member(zf, source_member, destination)
            copied_members.add(source_member)

            dependencies: list[str] = []
            if destination.suffix.lower() == ".gltf":
                dependencies = gltf_dependency_members(
                    zf,
                    source_member,
                )
                for dep_member in dependencies:
                    dep_rel = relative_member(dep_member, common_root)
                    dep_destination = pack_root / dep_rel
                    if dep_member not in copied_members:
                        copy_member(zf, dep_member, dep_destination)
                        copied_members.add(dep_member)

            asset_id = (
                pack_slug
                + ":"
                + Path(rel).with_suffix("").as_posix()
            )
            assets.append(
                {
                    "id": asset_id,
                    "pack": pack_slug,
                    "source_archive": archive.name,
                    "source_member": source_member,
                    "format": destination.suffix.lower().lstrip("."),
                    "res_path": (
                        "res://"
                        + destination.relative_to(GODOT_ROOT).as_posix()
                    ),
                    "dependencies": [
                        relative_member(dep, common_root)
                        for dep in dependencies
                    ],
                }
            )

        license_files = copy_license_files(
            zf,
            pack_root,
            common_root,
        )

    return {
        "pack": pack_slug,
        "archive_name": archive.name,
        "archive_path": str(archive),
        "sha256": archive_hash,
        "asset_count": len(assets),
        "license_files": license_files,
        "assets": assets,
    }


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {
            "schema_version": "1.0",
            "packs": [],
            "assets": [],
        }
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": "1.0",
            "packs": [],
            "assets": [],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", action="append", default=[])
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--include-all-3d-zips", action="store_true")
    args = parser.parse_args()

    source_dirs = candidate_dirs(
        [Path(value) for value in args.source_dir]
    )
    archives = [
        archive
        for archive in discover_archives(
            source_dirs,
            args.include_all_3d_zips,
        )
        if zip_has_3d_assets(archive)
    ]

    if not archives:
        print("No supported 3D asset ZIPs found.")
        print("Searched:")
        for directory in source_dirs:
            print(f"  - {directory}")
        return 2

    if args.clean and VAULT_ROOT.exists():
        shutil.rmtree(VAULT_ROOT)

    VAULT_ROOT.mkdir(parents=True, exist_ok=True)

    previous = load_manifest()
    previous_by_name = {
        pack.get("archive_name"): pack
        for pack in previous.get("packs", [])
    }

    packs: list[dict] = []
    all_assets: list[dict] = []
    installed_packs = 0
    reused_packs = 0

    for archive in archives:
        digest = archive_sha256(archive)
        previous_pack = previous_by_name.get(archive.name)

        if (
            not args.clean
            and previous_pack
            and previous_pack.get("sha256") == digest
        ):
            pack_root = VAULT_ROOT / str(previous_pack.get("pack", ""))
            if pack_root.is_dir():
                packs.append(previous_pack)
                all_assets.extend(previous_pack.get("assets", []))
                reused_packs += 1
                print(
                    f"Reused {archive.name}: "
                    f"{previous_pack.get('asset_count', 0)} assets"
                )
                continue

        result = install_archive(archive, digest)
        packs.append(result)
        all_assets.extend(result["assets"])
        installed_packs += 1
        print(
            f"Installed {archive.name}: "
            f"{result['asset_count']} assets"
        )

    manifest = {
        "schema_version": "1.0",
        "generated_by": "tools/install_full_asset_vault.py",
        "pack_count": len(packs),
        "asset_count": len(all_assets),
        "packs": packs,
        "assets": all_assets,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print("")
    print(f"Asset Vault packs: {len(packs)}")
    print(f"Asset Vault 3D assets: {len(all_assets)}")
    print(f"Installed/updated packs: {installed_packs}")
    print(f"Reused unchanged packs: {reused_packs}")
    print(f"Godot destination: {VAULT_ROOT}")
    print("")
    print("Godot will import this vault once.")
    print(
        "Future world iterations can reuse the same local assets "
        "without extracting pack subsets again."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
