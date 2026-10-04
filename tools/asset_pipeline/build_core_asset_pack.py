from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from PIL import Image
import trimesh


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO_ROOT / "assets" / "catalogs" / "core_cc0_seed_v1.json"


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _parse_sources(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--source must use pack_id=/path/to/source.zip")
        pack_id, raw_path = value.split("=", 1)
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        result[pack_id] = path
    return result


def _downscale_textures(root: Path, max_size: int) -> None:
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        try:
            with Image.open(path) as image:
                if max(image.size) <= max_size:
                    continue
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                options: dict[str, object] = {"optimize": True}
                if path.suffix.lower() in {".jpg", ".jpeg"}:
                    options["quality"] = 88
                image.save(path, **options)
        except OSError:
            # A malformed/unsupported image should fail later when the source
            # glTF tries to load it. Do not silently replace it.
            continue


def _normalize_scene(scene: trimesh.Scene) -> None:
    bounds = scene.bounds
    if bounds is None:
        raise ValueError("3D source has no measurable bounds.")
    center_x = float(bounds[0][0] + bounds[1][0]) / 2.0
    center_z = float(bounds[0][2] + bounds[1][2]) / 2.0
    min_y = float(bounds[0][1])
    scene.apply_transform(
        trimesh.transformations.translation_matrix(
            [-center_x, -min_y, -center_z]
        )
    )


def _scene_stats(scene: trimesh.Scene) -> dict[str, object]:
    bounds = scene.bounds
    if bounds is None:
        bounds_list = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        extents = [0.0, 0.0, 0.0]
    else:
        bounds_list = bounds.tolist()
        extents = (bounds[1] - bounds[0]).tolist()

    vertices = 0
    triangles = 0
    for geometry in scene.geometry.values():
        vertices += len(geometry.vertices)
        faces = getattr(geometry, "faces", None)
        if faces is not None:
            triangles += len(faces)

    return {
        "bounds": bounds_list,
        "extents": extents,
        "vertices": vertices,
        "triangles": triangles,
        "geometry_count": len(scene.geometry),
    }


def build_pack(
    *,
    catalog_path: Path,
    sources: dict[str, Path],
    output_zip: Path,
) -> dict[str, object]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = catalog["packs"]
    selected = catalog["assets"]

    missing = sorted({item["pack"] for item in selected} - set(sources))
    if missing:
        raise ValueError(
            "Missing source ZIP(s): " + ", ".join(missing)
        )

    work = Path(tempfile.mkdtemp(prefix="mini_utopia_asset_pack_"))
    pack_root = work / "pack"
    glb_root = pack_root / "glb"
    license_root = pack_root / "licenses"
    glb_root.mkdir(parents=True)
    license_root.mkdir(parents=True)

    extracted: dict[str, Path] = {}
    try:
        licenses: dict[str, object] = {}
        for pack_id, source_zip in sources.items():
            spec = packs[pack_id]
            target = work / "sources" / pack_id
            target.mkdir(parents=True)
            with zipfile.ZipFile(source_zip) as archive:
                try:
                    license_bytes = archive.read(spec["license_entry"])
                except KeyError as exc:
                    raise ValueError(
                        f"{pack_id} does not contain expected license file "
                        f"{spec['license_entry']}"
                    ) from exc
                archive.extractall(target)

            license_name = f"{pack_id}_LICENSE.txt"
            (license_root / license_name).write_bytes(license_bytes)
            licenses[pack_id] = {
                "license_id": spec["license_id"],
                "source_name": spec["source_name"],
                "source_url": spec["source_url"],
                "license_file": f"licenses/{license_name}",
            }

            texture_max = spec.get("texture_max_size")
            if texture_max:
                _downscale_textures(target / spec["prefix"], int(texture_max))
            extracted[pack_id] = target

        entries: list[dict[str, object]] = []
        for item in selected:
            pack_id = item["pack"]
            pack = packs[pack_id]
            source_rel = pack["prefix"] + item["file"]
            source_path = extracted[pack_id] / source_rel
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Catalog entry missing from {pack_id}: {source_rel}"
                )

            scene = trimesh.load(source_path, force="scene", process=False)
            _normalize_scene(scene)
            stats = _scene_stats(scene)
            glb = scene.export(file_type="glb")

            digest = hashlib.sha256(glb).hexdigest()
            stem = Path(item["file"]).stem
            asset_key = f"mu_{item['category']}_{_slug(stem)}"
            filename = f"{asset_key}_{digest[:8]}.glb"
            (glb_root / filename).write_bytes(glb)

            entries.append(
                {
                    "asset_key": asset_key,
                    "display_name": stem.replace("_", " "),
                    "category": item["category"],
                    "semantic_keys": item["semantic_keys"],
                    "source_pack": pack_id,
                    "source_entry": source_rel,
                    "source_name": pack["source_name"],
                    "source_url": pack["source_url"],
                    "license_id": pack["license_id"],
                    "attribution_required": False,
                    "glb_path": f"glb/{filename}",
                    "sha256": digest,
                    "byte_size": len(glb),
                    "style_status": "raw",
                    "normalization": {
                        "up_axis": "y",
                        "forward_axis": "z",
                        "ground_aligned": True,
                        "centered_xz": True,
                        "meters_per_unit": 1.0,
                        "base_uniform_scale": 1.0,
                        "material_profile": "source",
                    },
                    "variant_policy": {
                        "allow_uniform_scale": True,
                        "allow_palette_override": True,
                        "allow_material_override": True,
                        "allow_texture_swap": False,
                        "allow_geometry_edit": False,
                    },
                    "tags": ["cc0", "core-asset-pack"],
                    "stats": stats,
                }
            )

        manifest = {
            "schema_version": "1.0",
            "name": "Mini Utopia Core Asset Pack v1",
            "style_target": "Mini Utopia Visual DNA v1",
            "licenses": licenses,
            "assets": entries,
            "summary": {
                "asset_count": len(entries),
                "by_category": dict(
                    Counter(item["category"] for item in entries)
                ),
                "by_source": dict(
                    Counter(item["source_pack"] for item in entries)
                ),
                "total_glb_bytes": sum(
                    int(item["byte_size"]) for item in entries
                ),
            },
        }
        (pack_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (pack_root / "README.txt").write_text(
            "Mini Utopia Core Asset Pack v1\n"
            "Source assets remain under their recorded CC0 licenses.\n"
            "GLBs are Y-up, ground-aligned and centered on X/Z.\n"
            "Style status remains raw until Mini Utopia review/normalization.\n",
            encoding="utf-8",
        )

        output_zip = output_zip.expanduser().resolve()
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        base = output_zip.with_suffix("")
        archive_path = shutil.make_archive(
            str(base), "zip", root_dir=pack_root
        )
        if Path(archive_path) != output_zip:
            Path(archive_path).replace(output_zip)
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a normalized Mini Utopia reusable GLB asset pack."
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Curated asset catalog JSON.",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Source ZIP mapping: pack_id=/path/to/source.zip (repeatable).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output portable asset-pack ZIP.",
    )
    args = parser.parse_args()

    manifest = build_pack(
        catalog_path=args.catalog,
        sources=_parse_sources(args.source),
        output_zip=args.output,
    )
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()
