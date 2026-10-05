from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from studio.storage.base import ObjectStorage


@dataclass(frozen=True)
class GodotHeroBundle:
    filename: str
    payload: bytes
    manifest: dict


@dataclass(frozen=True)
class GodotHeroInstallResult:
    hero_path: Path
    manifest_path: Path


class GodotHeroExportService:
    """Package one stored Hero GLB for the Godot runtime.

    The bundle intentionally keeps Hero geometry unified. Blueprint identities
    remain metadata, but Godot receives one GLB source per Hero cluster.
    """

    def __init__(self, storage: ObjectStorage):
        self.storage = storage

    def build_bundle(
        self,
        *,
        hero: dict,
        target_size: tuple[float, float, float],
        position: tuple[float, float, float] = (0.0, 4.5, -7.0),
        collision_proxy: bool | None = None,
    ) -> GodotHeroBundle:
        asset_path = str(hero.get("asset_path") or "").strip()
        if not asset_path:
            raise ValueError("Hero asset_path is required.")

        glb = self.storage.get_bytes(asset_path)
        if len(glb) < 12 or glb[:4] != b"glTF":
            raise ValueError("Stored Hero asset is not a valid GLB payload.")

        hero_id = str(hero.get("element_id") or "hero").strip() or "hero"
        display_name = str(hero.get("name") or hero_id).strip() or hero_id
        slug = self._slug(hero_id)
        glb_name = f"{slug}.glb"

        render_strategy = (
            "unified_glb"
            if hero.get("cluster_id")
            else "single_object"
        )
        effective_collision_proxy = (
            render_strategy == "unified_glb"
            if collision_proxy is None
            else bool(collision_proxy)
        )

        manifest = {
            "schema_version": "0.1",
            "heroes": [
                {
                    "hero_id": hero_id,
                    "display_name": display_name,
                    "source": f"res://assets/external/heroes/{glb_name}",
                    "position": [float(value) for value in position],
                    "target_size": [float(value) for value in target_size],
                    "collision_proxy": effective_collision_proxy,
                    "source_asset_path": asset_path,
                    "source_model": str(hero.get("model") or ""),
                    "source_status": str(hero.get("status") or ""),
                    "cluster_id": str(hero.get("cluster_id") or ""),
                    "member_element_ids": list(
                        hero.get("member_element_ids") or []
                    ),
                    "render_strategy": render_strategy,
                    "reference_mode": str(
                        hero.get("reference_mode") or ""
                    ),
                }
            ],
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(
            buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.writestr(f"heroes/{glb_name}", glb)
            archive.writestr(
                "heroes/hero_manifest.json",
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )
            archive.writestr(
                "README.txt",
                (
                    "Mini Utopia Godot Hero Bundle\n\n"
                    "Unzip this bundle into:\n"
                    "godot/assets/external/\n\n"
                    "After extraction you should have:\n"
                    f"godot/assets/external/heroes/{glb_name}\n"
                    "godot/assets/external/heroes/hero_manifest.json\n\n"
                    "Restart or rescan the Godot project, then run the game.\n"
                ).encode("utf-8"),
            )

        return GodotHeroBundle(
            filename=f"mini-utopia-{slug}-godot.zip",
            payload=buffer.getvalue(),
            manifest=manifest,
        )

    def install_bundle(
        self,
        *,
        bundle: GodotHeroBundle,
        repository_root: Path,
    ) -> GodotHeroInstallResult:
        """Install a prepared Hero bundle into this checkout's Godot project."""
        repository_root = repository_root.resolve()
        godot_project = repository_root / "godot" / "project.godot"
        if not godot_project.exists():
            raise ValueError(
                "Godot project not found under repository_root/godot/project.godot."
            )

        destination = (
            repository_root
            / "godot"
            / "assets"
            / "external"
            / "heroes"
        )
        destination.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(bundle.payload), "r") as archive:
            manifest_member = "heroes/hero_manifest.json"
            if manifest_member not in archive.namelist():
                raise ValueError("Hero bundle is missing hero_manifest.json.")

            manifest = json.loads(
                archive.read(manifest_member).decode("utf-8")
            )
            heroes = manifest.get("heroes") or []
            if not heroes:
                raise ValueError("Hero bundle manifest has no Hero entries.")

            source = str(heroes[0].get("source") or "")
            prefix = "res://assets/external/heroes/"
            if not source.startswith(prefix):
                raise ValueError(
                    "Hero bundle manifest source is not a Godot Hero path."
                )

            glb_name = source[len(prefix):]
            if not glb_name or "/" in glb_name or "\\" in glb_name:
                raise ValueError(
                    "Hero bundle manifest contains an unsafe GLB filename."
                )

            glb_member = f"heroes/{glb_name}"
            if glb_member not in archive.namelist():
                raise ValueError(
                    "Hero bundle is missing the referenced GLB."
                )

            hero_bytes = archive.read(glb_member)
            if len(hero_bytes) < 12 or hero_bytes[:4] != b"glTF":
                raise ValueError(
                    "Hero bundle contains an invalid GLB payload."
                )

            hero_path = destination / glb_name
            manifest_path = destination / "hero_manifest.json"
            hero_path.write_bytes(hero_bytes)
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return GodotHeroInstallResult(
            hero_path=hero_path,
            manifest_path=manifest_path,
        )

    @staticmethod
    def _slug(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9_-]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "hero"
