from __future__ import annotations

import io
import json
import zipfile

import pytest

from studio.services.godot_hero_export_service import GodotHeroExportService
from studio.storage.local import LocalObjectStorage


def _valid_glb() -> bytes:
    # Minimal header is enough for bundle validation in this service test.
    return b"glTF" + (2).to_bytes(4, "little") + (12).to_bytes(4, "little")


def test_build_bundle_contains_unified_glb_and_manifest(tmp_path):
    storage = LocalObjectStorage(tmp_path)
    storage.put_bytes("assets/library/hero.glb", _valid_glb())
    service = GodotHeroExportService(storage)

    bundle = service.build_bundle(
        hero={
            "element_id": "SCENE_WHALE",
            "name": "Gentle Sky Whale Station",
            "asset_path": "assets/library/hero.glb",
            "model": "pixal3d",
            "status": "generated",
            "reference_mode": "generated_unified_cluster_v1",
            "cluster_id": "HERO_CLUSTER_CLOUD_WHALE",
            "member_element_ids": [
                "SCENE_WHALE",
                "SCENE_GARDEN",
                "SCENE_LIGHTHOUSE",
            ],
        },
        target_size=(18.0, 8.0, 9.0),
    )

    with zipfile.ZipFile(io.BytesIO(bundle.payload), "r") as archive:
        names = set(archive.namelist())
        assert "heroes/scene_whale.glb" in names
        assert "heroes/hero_manifest.json" in names
        manifest = json.loads(
            archive.read("heroes/hero_manifest.json").decode("utf-8")
        )

    hero = manifest["heroes"][0]
    assert hero["hero_id"] == "SCENE_WHALE"
    assert hero["source"] == (
        "res://assets/external/heroes/scene_whale.glb"
    )
    assert hero["target_size"] == [18.0, 8.0, 9.0]
    assert hero["source_asset_path"] == "assets/library/hero.glb"
    assert hero["cluster_id"] == "HERO_CLUSTER_CLOUD_WHALE"
    assert hero["render_strategy"] == "unified_glb"
    assert hero["collision_proxy"] is True
    assert hero["reference_mode"] == "generated_unified_cluster_v1"
    assert hero["member_element_ids"] == [
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
    ]


def test_build_bundle_rejects_invalid_glb(tmp_path):
    storage = LocalObjectStorage(tmp_path)
    storage.put_bytes("bad.glb", b"not-a-glb")
    service = GodotHeroExportService(storage)

    with pytest.raises(ValueError, match="valid GLB"):
        service.build_bundle(
            hero={
                "element_id": "SCENE_BAD",
                "asset_path": "bad.glb",
            },
            target_size=(1.0, 1.0, 1.0),
        )


def test_install_bundle_writes_glb_and_manifest(tmp_path):
    storage = LocalObjectStorage(tmp_path / "storage")
    storage.put_bytes("assets/library/hero.glb", _valid_glb())
    service = GodotHeroExportService(storage)
    bundle = service.build_bundle(
        hero={
            "element_id": "SCENE_WHALE",
            "name": "Unified Whale",
            "asset_path": "assets/library/hero.glb",
            "status": "generated",
            "reference_mode": "generated_unified_cluster_v1",
            "cluster_id": "HERO_CLUSTER_WHALE",
            "member_element_ids": ["SCENE_WHALE", "SCENE_GARDEN"],
        },
        target_size=(18.0, 8.0, 9.0),
    )

    repo_root = tmp_path / "repo"
    (repo_root / "godot").mkdir(parents=True)
    (repo_root / "godot" / "project.godot").write_text(
        "[application]\nconfig/name=\"Mini Utopia\"\n",
        encoding="utf-8",
    )

    installed = service.install_bundle(
        bundle=bundle,
        repository_root=repo_root,
    )

    assert installed.hero_path.exists()
    assert installed.hero_path.read_bytes() == _valid_glb()
    assert installed.manifest_path.exists()

    manifest = json.loads(
        installed.manifest_path.read_text(encoding="utf-8")
    )
    hero = manifest["heroes"][0]
    assert hero["render_strategy"] == "unified_glb"
    assert hero["reference_mode"] == "generated_unified_cluster_v1"


def test_install_bundle_requires_godot_checkout(tmp_path):
    storage = LocalObjectStorage(tmp_path / "storage")
    storage.put_bytes("assets/library/hero.glb", _valid_glb())
    service = GodotHeroExportService(storage)
    bundle = service.build_bundle(
        hero={
            "element_id": "SCENE_WHALE",
            "asset_path": "assets/library/hero.glb",
        },
        target_size=(1.0, 1.0, 1.0),
    )

    with pytest.raises(ValueError, match="Godot project not found"):
        service.install_bundle(
            bundle=bundle,
            repository_root=tmp_path / "not-a-repo",
        )


def test_single_object_bundle_keeps_collision_disabled_by_default(tmp_path):
    storage = LocalObjectStorage(tmp_path)
    storage.put_bytes("assets/library/hero.glb", _valid_glb())
    service = GodotHeroExportService(storage)

    bundle = service.build_bundle(
        hero={
            "element_id": "SCENE_PROP",
            "name": "Decorative Prop",
            "asset_path": "assets/library/hero.glb",
        },
        target_size=(2.0, 2.0, 2.0),
    )

    hero = bundle.manifest["heroes"][0]
    assert hero["render_strategy"] == "single_object"
    assert hero["collision_proxy"] is False
