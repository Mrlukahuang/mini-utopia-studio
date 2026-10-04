from __future__ import annotations

import struct

import pytest

from studio.core.enums import AssetType
from studio.models.reusable_asset import (
    ReusableAssetSourceSpec,
    ReusableAssetVariantOverrides,
    ReusableAssetVariantPolicy,
)
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.reusable_asset_library_service import (
    REUSABLE_GLB_METADATA_KEY,
    ReusableAssetLibraryService,
)
from studio.storage.local import LocalObjectStorage


def _glb(payload: bytes = b"") -> bytes:
    # Minimal GLB-like binary sufficient for validating the standard 12-byte
    # header. Production assets contain JSON/BIN chunks after this header.
    total = 12 + len(payload)
    return b"glTF" + struct.pack("<II", 2, total) + payload


def _source() -> ReusableAssetSourceSpec:
    return ReusableAssetSourceSpec(
        origin_kind="cc0_library",
        source_name="Quaternius",
        source_url="https://quaternius.com/",
        license_id="CC0-1.0",
        attribution_required=False,
    )


def _service(tmp_path) -> ReusableAssetLibraryService:
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    return ReusableAssetLibraryService(repo, storage)


def test_import_reusable_glb_is_content_addressed_and_persistent(tmp_path):
    service = _service(tmp_path)
    payload = _glb(b"tree")

    asset = service.import_glb(
        payload=payload,
        display_name="Round Tree 01",
        category="tree",
        semantic_keys=["round_tree", "tree"],
        source=_source(),
        tags=["nature", "cc0"],
    )

    spec = asset.metadata[REUSABLE_GLB_METADATA_KEY]
    assert asset.asset_type == AssetType.PROP
    assert asset.asset_id.startswith("PROP_")
    assert spec["category"] == "tree"
    assert spec["source"]["license_id"] == "CC0-1.0"
    assert spec["storage_path"].startswith("assets/library/")
    assert service.storage.get_bytes(spec["storage_path"]) == payload


def test_importing_same_glb_twice_reuses_existing_asset(tmp_path):
    service = _service(tmp_path)
    payload = _glb(b"same-tree")

    first = service.import_glb(
        payload=payload,
        display_name="Tree A",
        category="tree",
        semantic_keys=["tree"],
        source=_source(),
    )
    second = service.import_glb(
        payload=payload,
        display_name="Tree B duplicate",
        category="tree",
        semantic_keys=["tree"],
        source=_source(),
    )

    assert second.asset_id == first.asset_id
    assert len(service.list_reusable()) == 1


def test_derived_color_variant_reuses_glb_bytes_without_gpu_regeneration(tmp_path):
    service = _service(tmp_path)
    base = service.import_glb(
        payload=_glb(b"tree-base"),
        display_name="Round Tree",
        category="tree",
        semantic_keys=["round_tree"],
        source=_source(),
    )

    pink = service.create_variant(
        base_asset_id=base.asset_id,
        display_name="Round Tree - Strawberry Pink",
        overrides=ReusableAssetVariantOverrides(
            palette_hex_by_role={"foliage": "#F7B7D2"},
        ),
    )

    base_spec = base.metadata[REUSABLE_GLB_METADATA_KEY]
    pink_spec = pink.metadata[REUSABLE_GLB_METADATA_KEY]
    assert pink.asset_id != base.asset_id
    assert pink_spec["parent_asset_id"] == base.asset_id
    assert pink_spec["storage_path"] == base_spec["storage_path"]
    assert pink_spec["sha256"] == base_spec["sha256"]
    assert pink_spec["variant_overrides"]["palette_hex_by_role"]["foliage"] == "#F7B7D2"


def test_variant_policy_can_block_recolor(tmp_path):
    service = _service(tmp_path)
    base = service.import_glb(
        payload=_glb(b"locked-prop"),
        display_name="Locked Prop",
        category="prop",
        semantic_keys=["locked_prop"],
        source=_source(),
        variant_policy=ReusableAssetVariantPolicy(
            allow_palette_override=False,
        ),
    )

    with pytest.raises(ValueError, match="palette overrides"):
        service.create_variant(
            base_asset_id=base.asset_id,
            display_name="Forbidden Pink",
            overrides=ReusableAssetVariantOverrides(
                palette_hex_by_role={"primary": "#F7B7D2"},
            ),
        )


def test_approved_assets_can_be_found_by_semantic_key(tmp_path):
    service = _service(tmp_path)
    asset = service.import_glb(
        payload=_glb(b"mushroom"),
        display_name="Dream Mushroom",
        category="mushroom",
        semantic_keys=["mushroom", "dream_mushroom"],
        source=_source(),
    )

    assert service.find_for_semantic_key("mushroom") == []
    service.set_style_status(asset.asset_id, "approved")
    matches = service.find_for_semantic_key("MUSHROOM")
    assert [item.asset_id for item in matches] == [asset.asset_id]


def test_invalid_binary_is_rejected(tmp_path):
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="binary glTF"):
        service.import_glb(
            payload=b"not-a-glb",
            display_name="Broken",
            category="prop",
            semantic_keys=["broken"],
            source=_source(),
        )
