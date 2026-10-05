#!/usr/bin/env python3
"""Install the first Mini Utopia Golden Style Anchor lineup from local source ZIPs.

The source archives remain immutable. This script extracts only the curated anchor
files and direct glTF dependencies into godot/assets/external/golden/, which is
ignored by git.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "assets" / "catalogs" / "golden_style_anchors_v1.json"


def _candidate_dirs(extra: list[Path]) -> list[Path]:
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
    seen: set[Path] = set()
    result: list[Path] = []
    for item in raw:
        try:
            item = item.expanduser().resolve()
        except OSError:
            continue
        if item not in seen and item.exists() and item.is_dir():
            seen.add(item)
            result.append(item)
    return result


def _find_archive(names: list[str], dirs: list[Path]) -> Path | None:
    for directory in dirs:
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def _safe_member(member: str) -> str:
    normalized = posixpath.normpath(member).lstrip("/")
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"unsafe zip member: {member}")
    return normalized


def _copy_member(zf: zipfile.ZipFile, member: str, destination: Path) -> None:
    member = _safe_member(member)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def _is_external_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    return bool(parsed.scheme) or uri.startswith("data:")


def _install_anchor(
    zf: zipfile.ZipFile,
    entry: dict,
    install_root: Path,
) -> dict:
    source_member = _safe_member(entry["source_member"])
    source_name = Path(source_member).name
    destination_dir = install_root / entry["id"]
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_file = destination_dir / source_name
    _copy_member(zf, source_member, destination_file)

    copied = [destination_file]
    suffix = destination_file.suffix.lower()
    if suffix == ".gltf":
        data = json.loads(zf.read(source_member))
        base_dir = posixpath.dirname(source_member)
        uris: list[str] = []
        for buffer in data.get("buffers", []):
            uri = buffer.get("uri")
            if uri:
                uris.append(uri)
        for image in data.get("images", []):
            uri = image.get("uri")
            if uri:
                uris.append(uri)

        for uri in sorted(set(uris)):
            if _is_external_uri(uri):
                continue
            source_dependency = _safe_member(posixpath.join(base_dir, uri))
            relative_dependency = Path(uri)
            destination_dependency = destination_dir / relative_dependency
            _copy_member(zf, source_dependency, destination_dependency)
            copied.append(destination_dependency)

    relative_res = destination_file.relative_to(REPO_ROOT / "godot").as_posix()
    installed = dict(entry)
    installed["res_path"] = f"res://{relative_res}"
    installed["installed_files"] = [
        path.relative_to(REPO_ROOT / "godot").as_posix() for path in copied
    ]
    return installed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        action="append",
        default=[],
        help="Directory containing downloaded source ZIPs. May be supplied more than once.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the existing locally installed Golden anchor directory first.",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    install_root = REPO_ROOT / manifest["install_root"]
    if args.clean and install_root.exists():
        shutil.rmtree(install_root)

    install_root.mkdir(parents=True, exist_ok=True)
    licenses_root = install_root / "_licenses"
    licenses_root.mkdir(parents=True, exist_ok=True)

    search_dirs = _candidate_dirs([Path(p) for p in args.source_dir])
    pack_archives: dict[str, Path] = {}
    missing: list[tuple[str, list[str]]] = []

    for pack_id, pack in manifest["packs"].items():
        archive = _find_archive(pack["archive_candidates"], search_dirs)
        if archive is None:
            missing.append((pack_id, pack["archive_candidates"]))
        else:
            pack_archives[pack_id] = archive

    if missing:
        print("Missing source ZIPs:")
        for pack_id, names in missing:
            print(f"  - {pack_id}: {' or '.join(names)}")
        print("\nSearched:")
        for directory in search_dirs:
            print(f"  - {directory}")
        print("\nRe-run with --source-dir /path/to/your/downloads if needed.")
        return 2

    installed_entries: list[dict] = []
    for pack_id, archive_path in pack_archives.items():
        pack = manifest["packs"][pack_id]
        with zipfile.ZipFile(archive_path) as zf:
            license_member = pack.get("license_member")
            if license_member:
                license_destination = licenses_root / f"{pack_id}.txt"
                _copy_member(zf, license_member, license_destination)

            for entry in manifest["anchors"]:
                if entry["pack"] != pack_id:
                    continue
                installed = _install_anchor(zf, entry, install_root)
                installed["source_archive"] = archive_path.name
                installed_entries.append(installed)
                print(f"Installed {entry['id']}")

    installed_manifest = {
        "schema_version": "1.0",
        "source_manifest": "assets/catalogs/golden_style_anchors_v1.json",
        "count": len(installed_entries),
        "anchors": installed_entries,
    }
    (install_root / "installed_manifest.json").write_text(
        json.dumps(installed_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nInstalled {len(installed_entries)} Golden Style Anchors.")
    print(f"Godot destination: {install_root}")
    print("Return to Godot, let Import finish, then run the Calibration Lab.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
