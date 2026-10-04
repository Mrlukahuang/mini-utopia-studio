from __future__ import annotations

import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.reusable_asset import (
    ReusableAssetPackManifest,
    ReusableAssetSourceSpec,
)
from studio.services.reusable_asset_library_service import ReusableAssetLibraryService


class ReusableAssetPackService:
    """Import a portable normalized asset-pack ZIP into ObjectStorage/metadata.

    The offline pack builder is responsible for converting third-party glTF/GLB
    sources into web-ready GLB. Runtime import deliberately stays lightweight:
    it validates manifest paths, byte counts, SHA-256 digests and then delegates
    deduplicated storage to ReusableAssetLibraryService.
    """

    def __init__(self, library: ReusableAssetLibraryService):
        self.library = library

    @staticmethod
    def _safe_member(path: str) -> str:
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"Unsafe asset-pack member path: {path}")
        if normalized.suffix.lower() != ".glb":
            raise ValueError(f"Asset-pack entry is not a GLB: {path}")
        return normalized.as_posix()

    def inspect_manifest(self, payload: bytes) -> ReusableAssetPackManifest:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                raw = archive.read("manifest.json")
        except (zipfile.BadZipFile, KeyError) as exc:
            raise ValueError("Asset pack must be a ZIP containing manifest.json.") from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Asset pack manifest.json is not valid UTF-8 JSON.") from exc
        manifest = ReusableAssetPackManifest.model_validate(data)
        if not manifest.assets:
            raise ValueError("Asset pack manifest contains no assets.")
        return manifest

    def import_pack(self, payload: bytes) -> list[Asset]:
        manifest = self.inspect_manifest(payload)
        imported: list[Asset] = []

        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for entry in manifest.assets:
                member = self._safe_member(entry.glb_path)
                try:
                    glb = archive.read(member)
                except KeyError as exc:
                    raise ValueError(
                        f"Asset pack is missing GLB payload: {member}"
                    ) from exc

                if len(glb) != entry.byte_size:
                    raise ValueError(
                        f"Asset pack byte-size mismatch for {entry.asset_key}: "
                        f"manifest={entry.byte_size}, actual={len(glb)}"
                    )
                digest = hashlib.sha256(glb).hexdigest()
                if digest != entry.sha256:
                    raise ValueError(
                        f"Asset pack SHA-256 mismatch for {entry.asset_key}."
                    )

                asset = self.library.import_glb(
                    payload=glb,
                    display_name=entry.display_name,
                    category=entry.category,
                    semantic_keys=entry.semantic_keys,
                    source=ReusableAssetSourceSpec(
                        origin_kind="cc0_library",
                        source_name=entry.source_name,
                        source_url=entry.source_url,
                        license_id=entry.license_id,
                        attribution_required=entry.attribution_required,
                    ),
                    asset_type=AssetType.PROP,
                    tags=list(
                        dict.fromkeys(
                            [
                                "core-asset-pack",
                                entry.category,
                                *entry.tags,
                                *(
                                    [f"source:{entry.source_pack}"]
                                    if entry.source_pack
                                    else []
                                ),
                            ]
                        )
                    ),
                    normalization=entry.normalization,
                    variant_policy=entry.variant_policy,
                )

                # Keep offline pack audit provenance beside the stable reusable
                # GLB record without changing the immutable content hash.
                asset.metadata.setdefault("asset_pack", {})
                asset.metadata["asset_pack"].update(
                    {
                        "pack_name": manifest.name,
                        "asset_key": entry.asset_key,
                        "source_pack": entry.source_pack,
                        "source_entry": entry.source_entry,
                    }
                )
                self.library.repository.save_asset(asset)

                if entry.style_status != "raw":
                    asset = self.library.set_style_status(
                        asset.asset_id, entry.style_status
                    )
                imported.append(asset)

        return imported
