from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass

from studio.storage.base import ObjectStorage


@dataclass(frozen=True)
class GodotHeroBundle:
    filename: str
    payload: bytes
    manifest: dict


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
        collision_proxy: bool = False,
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

        manifest = {
            "schema_version": "0.1",
            "heroes": [
                {
                    "hero_id": hero_id,
                    "display_name": display_name,
                    "source": f"res://assets/external/heroes/{glb_name}",
                    "position": [float(value) for value in position],
                    "target_size": [float(value) for value in target_size],
                    "collision_proxy": bool(collision_proxy),
                    "source_asset_path": asset_path,
                    "source_model": str(hero.get("model") or ""),
                    "source_status": str(hero.get("status") or ""),
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

    @staticmethod
    def _slug(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9_-]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "hero"
