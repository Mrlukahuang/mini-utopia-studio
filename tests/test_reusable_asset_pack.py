from __future__ import annotations

import hashlib
import io
import json
import struct
import zipfile

import pytest

from studio.models.reusable_asset import ReusableGLBSpec
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.reusable_asset_library_service import (
    REUSABLE_GLB_METADATA_KEY,
    ReusableAssetLibraryService,
)
from studio.services.reusable_asset_pack_service import ReusableAssetPackService
from studio.storage.local import LocalObjectStorage


def _glb(payload: bytes = b"asset") -> bytes:
    total = 12 + len(payload)
    return b"glTF" + struct.pack("<II", 2, total) + payload


def _pack(*, corrupt_hash: bool = False, missing_glb: bool = False) -> bytes:
    glb = _glb(b"tree")
    digest = hashlib.sha256(glb).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "name": "Mini Utopia Test Pack",
        "style_target": "Mini Utopia Visual DNA v1",
        "assets": [
            {
                "asset_key": "mu_tree_round_01",
                "display_name": "Round Tree 01",
                "category": "tree",
                "semantic_keys": ["tree", "round_tree"],
                "source_pack": "kaykit_forest",
                "source_entry": "Assets/gltf/Tree_1_A_Color1.gltf",
                "source_name": "KayKit",
                "source_url": "https://example.test/kaykit",
                "license_id": "CC0-1.0",
                "attribution_required": False,
                "glb_path": "glb/tree.glb",
                "sha256": "0" * 64 if corrupt_hash else digest,
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
                "tags": ["nature"],
            }
        ],
    }

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        if not missing_glb:
            archive.writestr("glb/tree.glb", glb)
    return output.getvalue()


def _service(tmp_path) -> ReusableAssetPackService:
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    return ReusableAssetPackService(ReusableAssetLibraryService(repo, storage))


def test_import_pack_validates_and_imports_cc0_asset(tmp_path):
    service = _service(tmp_path)

    imported = service.import_pack(_pack())

    assert len(imported) == 1
    asset = imported[0]
    spec = ReusableGLBSpec.model_validate(
        asset.metadata[REUSABLE_GLB_METADATA_KEY]
    )
    assert spec.category == "tree"
    assert spec.source.license_id == "CC0-1.0"
    assert spec.semantic_keys == ["tree", "round_tree"]
    assert asset.metadata["asset_pack"]["asset_key"] == "mu_tree_round_01"
    assert asset.metadata["asset_pack"]["source_pack"] == "kaykit_forest"
    assert service.library.storage.exists(spec.storage_path)


def test_importing_same_pack_twice_reuses_library_asset(tmp_path):
    service = _service(tmp_path)
    payload = _pack()

    first = service.import_pack(payload)
    second = service.import_pack(payload)

    assert second[0].asset_id == first[0].asset_id
    assert len(service.library.list_reusable()) == 1


def test_pack_rejects_sha_mismatch(tmp_path):
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        service.import_pack(_pack(corrupt_hash=True))


def test_pack_rejects_missing_glb(tmp_path):
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="missing GLB payload"):
        service.import_pack(_pack(missing_glb=True))


def test_pack_rejects_unsafe_member_path(tmp_path):
    service = _service(tmp_path)
    payload = _pack()
    with zipfile.ZipFile(io.BytesIO(payload)) as source:
        manifest = json.loads(source.read("manifest.json"))
        glb = source.read("glb/tree.glb")
    manifest["assets"][0]["glb_path"] = "../tree.glb"

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("../tree.glb", glb)

    with pytest.raises(ValueError, match="Unsafe asset-pack member path"):
        service.import_pack(output.getvalue())
