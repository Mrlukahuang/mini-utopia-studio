from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.character import CharacterProfile, EyeProfile
from studio.services.character_runtime_service import CharacterRuntimeService


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


def test_runtime_service_defaults_to_procedural_identity_colors():
    spec = CharacterRuntimeService().resolve(_character_asset())

    assert spec.mode == "procedural"
    assert spec.body_color_hex == "#F7B7D2"
    assert spec.accent_color_hex == "#B9E7D0"
    assert spec.hair_color_hex == "#5B4036"
    assert spec.eye_color_hex == "#7A5238"
    assert spec.animation_clips.idle == "Idle"
    assert spec.animation_clips.walk == "Walk"
    assert spec.animation_clips.run == "Run"


def test_runtime_service_switches_to_glb_when_model_data_is_present():
    spec = CharacterRuntimeService().resolve(
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
