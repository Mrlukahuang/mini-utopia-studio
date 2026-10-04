from __future__ import annotations

import hashlib

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset, AssetFile
from studio.models.reusable_asset import (
    ReusableAssetNormalizationSpec,
    ReusableAssetSourceSpec,
    ReusableAssetVariantOverrides,
    ReusableAssetVariantPolicy,
    ReusableGLBSpec,
)
from studio.repositories.base import StudioRepository
from studio.services.asset_service import slugify
from studio.storage.base import ObjectStorage


REUSABLE_GLB_METADATA_KEY = "reusable_glb"


class ReusableAssetLibraryService:
    """Persistent, reusable GLB library shared by many Worlds.

    Import is content-addressed and idempotent: the same GLB bytes are stored
    once and return the existing Asset record. Derived variants keep the same
    immutable GLB bytes and add non-destructive color/material/scale metadata.
    """

    def __init__(self, repository: StudioRepository, storage: ObjectStorage):
        self.repository = repository
        self.storage = storage

    @staticmethod
    def _validate_glb(payload: bytes) -> None:
        if len(payload) < 12 or payload[:4] != b"glTF":
            raise ValueError("Reusable asset must be a binary glTF 2.0 (.glb) file.")
        version = int.from_bytes(payload[4:8], "little")
        if version != 2:
            raise ValueError(f"Unsupported GLB version: {version}; expected 2.")
        declared_length = int.from_bytes(payload[8:12], "little")
        if declared_length != len(payload):
            raise ValueError(
                "Invalid GLB header length: "
                f"declared {declared_length}, received {len(payload)}."
            )

    @staticmethod
    def _spec(asset: Asset) -> ReusableGLBSpec | None:
        raw = asset.metadata.get(REUSABLE_GLB_METADATA_KEY)
        if not raw:
            return None
        return ReusableGLBSpec.model_validate(raw)

    def list_reusable(self) -> list[Asset]:
        return [
            asset
            for asset in self.repository.list_assets()
            if REUSABLE_GLB_METADATA_KEY in asset.metadata
            and asset.status != ReviewStatus.ARCHIVED
        ]

    def find_by_sha256(self, sha256: str) -> Asset | None:
        for asset in self.list_reusable():
            spec = self._spec(asset)
            if spec is not None and spec.sha256 == sha256 and not spec.parent_asset_id:
                return asset
        return None

    def find_for_semantic_key(
        self,
        semantic_key: str,
        *,
        approved_only: bool = True,
    ) -> list[Asset]:
        semantic_key = semantic_key.strip().lower()
        matches: list[Asset] = []
        for asset in self.list_reusable():
            spec = self._spec(asset)
            if spec is None:
                continue
            keys = {item.strip().lower() for item in spec.semantic_keys}
            if semantic_key not in keys:
                continue
            if approved_only and spec.style_status != "approved":
                continue
            matches.append(asset)
        return matches

    def import_glb(
        self,
        *,
        payload: bytes,
        display_name: str,
        category: str,
        semantic_keys: list[str],
        source: ReusableAssetSourceSpec,
        asset_type: AssetType = AssetType.PROP,
        tags: list[str] | None = None,
        normalization: ReusableAssetNormalizationSpec | None = None,
        variant_policy: ReusableAssetVariantPolicy | None = None,
    ) -> Asset:
        self._validate_glb(payload)
        if asset_type not in {AssetType.PROP, AssetType.VEHICLE, AssetType.WEARABLE}:
            raise ValueError(
                "Reusable world GLB assets must currently be prop, vehicle, or wearable."
            )

        digest = hashlib.sha256(payload).hexdigest()
        existing = self.find_by_sha256(digest)
        if existing is not None:
            return existing

        storage_path = f"assets/library/{digest[:2]}/{digest}.glb"
        if not self.storage.exists(storage_path):
            self.storage.put_bytes(storage_path, payload)

        spec = ReusableGLBSpec(
            category=category,
            semantic_keys=list(dict.fromkeys(semantic_keys)),
            storage_path=storage_path,
            sha256=digest,
            byte_size=len(payload),
            source=source,
            normalization=normalization or ReusableAssetNormalizationSpec(),
            variant_policy=variant_policy or ReusableAssetVariantPolicy(),
        )
        asset = Asset.create(
            asset_type,
            display_name=display_name,
            slug=slugify(display_name),
            description="Reusable Mini Utopia GLB asset.",
            tags=list(dict.fromkeys(tags or [])),
            metadata={REUSABLE_GLB_METADATA_KEY: spec.model_dump(mode="json")},
            files=[
                AssetFile(
                    role="glb",
                    path=storage_path,
                    mime_type="model/gltf-binary",
                )
            ],
        )
        self.repository.save_asset(asset)
        return asset

    def create_variant(
        self,
        *,
        base_asset_id: str,
        display_name: str,
        overrides: ReusableAssetVariantOverrides,
        semantic_keys: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Asset:
        base = self.repository.get_asset(base_asset_id)
        if base is None:
            raise ValueError(f"Reusable base asset not found: {base_asset_id}")
        base_spec = self._spec(base)
        if base_spec is None:
            raise ValueError(f"Asset is not a reusable GLB: {base_asset_id}")

        policy = base_spec.variant_policy
        if overrides.palette_hex_by_role and not policy.allow_palette_override:
            raise ValueError("This asset does not allow palette overrides.")
        if (
            overrides.roughness is not None or overrides.metalness is not None
        ) and not policy.allow_material_override:
            raise ValueError("This asset does not allow material overrides.")
        if overrides.uniform_scale != 1.0 and not policy.allow_uniform_scale:
            raise ValueError("This asset does not allow scale overrides.")
        if overrides.texture_replacements and not policy.allow_texture_swap:
            raise ValueError("This asset does not allow texture replacement.")

        variant_spec = base_spec.model_copy(
            update={
                "source": ReusableAssetSourceSpec(
                    origin_kind="derived",
                    source_name=f"Derived from {base.asset_id}",
                    source_url=base_spec.source.source_url,
                    license_id=base_spec.source.license_id,
                    attribution_required=base_spec.source.attribution_required,
                    generator_model=base_spec.source.generator_model,
                ),
                "semantic_keys": (
                    list(dict.fromkeys(semantic_keys))
                    if semantic_keys is not None
                    else list(base_spec.semantic_keys)
                ),
                "parent_asset_id": base.asset_id,
                "variant_overrides": overrides,
            }
        )
        asset = Asset.create(
            base.asset_type,
            display_name=display_name,
            slug=slugify(display_name),
            description=f"Derived reusable variant of {base.display_name}.",
            tags=list(dict.fromkeys(tags if tags is not None else base.tags)),
            metadata={
                REUSABLE_GLB_METADATA_KEY: variant_spec.model_dump(mode="json")
            },
            files=[
                AssetFile(
                    role="glb",
                    path=base_spec.storage_path,
                    mime_type="model/gltf-binary",
                )
            ],
        )
        self.repository.save_asset(asset)
        return asset

    def set_style_status(self, asset_id: str, status: str) -> Asset:
        asset = self.repository.get_asset(asset_id)
        if asset is None:
            raise ValueError(f"Reusable asset not found: {asset_id}")
        spec = self._spec(asset)
        if spec is None:
            raise ValueError(f"Asset is not a reusable GLB: {asset_id}")
        if status not in {"raw", "normalized", "approved"}:
            raise ValueError(f"Unsupported reusable asset style status: {status}")

        spec.style_status = status
        asset.metadata[REUSABLE_GLB_METADATA_KEY] = spec.model_dump(mode="json")
        if status == "approved":
            asset.status = ReviewStatus.APPROVED
        self.repository.save_asset(asset)
        return asset
