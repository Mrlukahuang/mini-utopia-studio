from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile, EyeProfile
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.storage.local import LocalObjectStorage


def _character_asset(*, runtime_3d=None):
    profile = CharacterProfile(
        favorite_color_hexes=["#F7B7D2", "#B9E7D0"],
        hair_or_fur_color_hex="#5B4036",
        eyes=EyeProfile(color_hex="#7A5238"),
    )
    return Asset.create(
        AssetType.CHARACTER,
        display_name="Vivian",
        slug="vivian",
        metadata={
            "character_profile": profile.model_dump(mode="json"),
            "runtime_3d": runtime_3d or {},
        },
    )


def _service(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    return repo, storage, CharacterRuntimeService(repo, storage)


def test_runtime_service_defaults_to_procedural_identity_colors(tmp_path):
    _, _, service = _service(tmp_path)
    spec = service.resolve(_character_asset())

    assert spec.mode == "procedural"
    assert spec.body_color_hex == "#F7B7D2"
    assert spec.accent_color_hex == "#B9E7D0"
    assert spec.hair_color_hex == "#5B4036"
    assert spec.eye_color_hex == "#7A5238"
    assert spec.animation_clips.idle == "Idle"
    assert spec.animation_clips.walk == "Walk"
    assert spec.animation_clips.run == "Run"


def test_runtime_service_switches_to_glb_when_model_data_is_present(tmp_path):
    _, _, service = _service(tmp_path)
    spec = service.resolve(
        _character_asset(
            runtime_3d={
                "model_data_uri": "data:model/gltf-binary;base64,AAAA",
                "scale": 1.25,
                "animation_clips": {
                    "idle": "Idle_Breath",
                    "walk": "Walk_Cycle",
                    "run": "Run_Cycle",
                },
            }
        )
    )

    assert spec.mode == "glb"
    assert spec.model_data_uri.startswith("data:model/gltf-binary")
    assert spec.scale == 1.25
    assert spec.animation_clips.idle == "Idle_Breath"
    assert spec.animation_clips.walk == "Walk_Cycle"
    assert spec.animation_clips.run == "Run_Cycle"


def test_attach_glb_saves_binary_path_and_resolves_data_uri(tmp_path):
    repo, storage, service = _service(tmp_path)
    asset = _character_asset()
    repo.save_asset(asset)

    updated = service.attach_glb(
        asset_id=asset.asset_id,
        payload=b"glTF" + b"\x00" * 20,
        scale=1.15,
        idle_clip="Idle_Breath",
        walk_clip="Walk_Cycle",
        run_clip="Run_Cycle",
    )

    runtime_meta = updated.metadata["runtime_3d"]
    assert runtime_meta["model_path"].endswith("character.glb")
    assert "model_data_uri" not in runtime_meta
    assert storage.exists(runtime_meta["model_path"])

    spec = service.resolve(repo.get_asset(asset.asset_id))
    assert spec.mode == "glb"
    assert spec.model_data_uri.startswith("data:model/gltf-binary;base64,")
    assert spec.scale == 1.15
    assert spec.animation_clips.walk == "Walk_Cycle"


def test_missing_glb_file_falls_back_to_procedural(tmp_path):
    repo, _, service = _service(tmp_path)
    asset = _character_asset(
        runtime_3d={
            "model_path": "assets/missing/runtime/character.glb",
            "animation_clips": {"idle": "Idle"},
        }
    )
    repo.save_asset(asset)

    spec = service.resolve(asset)

    assert spec.mode == "procedural"
    assert spec.model_data_uri is None


def test_attach_rejects_non_glb_payload(tmp_path):
    repo, _, service = _service(tmp_path)
    asset = _character_asset()
    repo.save_asset(asset)

    try:
        service.attach_glb(asset_id=asset.asset_id, payload=b"not-a-glb")
    except ValueError as exc:
        assert "binary glTF" in str(exc)
    else:
        raise AssertionError("Expected invalid GLB payload to be rejected.")
