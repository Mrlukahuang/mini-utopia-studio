from pathlib import Path

from studio.models.avatar import (
    AVATAR_RIG_FAMILY,
    AvatarAppearance,
    AvatarSocket,
    BodyType,
    avatar_socket_names,
)
from studio.models.character import CharacterProfile, EyeProfile
from studio.models.runtime_character import CharacterRuntimeSpec
from studio.services.asset_service import AssetService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.storage.local import LocalObjectStorage


ROOT = Path(__file__).resolve().parents[1]


def test_avatar_contract_locks_three_body_types_and_six_sockets():
    assert [item.value for item in BodyType] == [
        "slim",
        "standard",
        "chubby",
    ]
    assert avatar_socket_names() == (
        "Socket_Weapon_R",
        "Socket_Weapon_L",
        "Socket_Backpack",
        "Socket_Wings",
        "Socket_Accessory",
        "Socket_Headwear",
    )
    assert [item.value for item in AvatarSocket] == list(avatar_socket_names())


def test_avatar_appearance_serializes_and_reloads():
    appearance = AvatarAppearance(
        customized=True,
        body_type=BodyType.CHUBBY,
        species_head_id="species_head_sheep_v1",
        surface_type="wool",
        surface_color_hex="#F7F4ED",
        eye_style_id="eyes_round_soft_v1",
        eye_color_hex="#7A5238",
        hair_style_id="hair_bob_v1",
        hair_color_hex="#5B4036",
    )

    restored = AvatarAppearance.model_validate(
        appearance.model_dump(mode="json")
    )

    assert restored == appearance
    assert restored.rig_family == AVATAR_RIG_FAMILY
    assert restored.body_type == BodyType.CHUBBY


def test_legacy_character_payload_still_loads_with_default_avatar():
    legacy_payload = {
        "schema_version": "1.2",
        "character_type": "Human",
        "hair_or_fur_color_hex": "#112233",
        "eyes": {"color_hex": "#445566"},
    }

    profile = CharacterProfile.model_validate(legacy_payload)

    assert profile.schema_version == "1.2"
    assert profile.avatar.body_type == BodyType.STANDARD
    assert profile.avatar.customized is False


def _service(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    return CharacterRuntimeService(repo, storage)


def test_runtime_uses_custom_avatar_when_explicitly_customized(tmp_path):
    profile = CharacterProfile(
        favorite_color_hexes=["#AAAAAA", "#BBBBBB"],
        hair_or_fur_color_hex="#111111",
        eyes=EyeProfile(color_hex="#222222"),
        avatar=AvatarAppearance(
            customized=True,
            body_type=BodyType.SLIM,
            species_head_id="species_head_robot_v1",
            surface_type="metal",
            surface_color_hex="#DDEEFF",
            eye_style_id="eyes_robot_v1",
            eye_color_hex="#00AAFF",
            hair_style_id="hair_none",
            hair_color_hex="#333333",
        ),
    )
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Robot",
        slug="robot",
        metadata={
            "character_profile": profile.model_dump(mode="json"),
        },
    )

    spec = _service(tmp_path).resolve(asset)

    assert spec.rig_family == AVATAR_RIG_FAMILY
    assert spec.body_type == BodyType.SLIM
    assert spec.species_head_id == "species_head_robot_v1"
    assert spec.surface_type == "metal"
    assert spec.body_color_hex == "#DDEEFF"
    assert spec.eye_color_hex == "#00AAFF"
    assert spec.hair_color_hex == "#333333"
    assert spec.socket_names == avatar_socket_names()


def test_runtime_spec_defaults_to_shared_humanoid_contract():
    spec = CharacterRuntimeSpec()

    assert spec.rig_family == AVATAR_RIG_FAMILY
    assert spec.body_type == BodyType.STANDARD
    assert spec.socket_names == avatar_socket_names()


def test_godot_avatar_contract_and_smoke_scene_are_wired():
    contract = (
        ROOT / "godot" / "scripts" / "avatar_contract.gd"
    ).read_text(encoding="utf-8")
    preview = (
        ROOT / "godot" / "scripts" / "avatar_contract_preview.gd"
    ).read_text(encoding="utf-8")
    scene = (
        ROOT / "godot" / "scenes" / "avatar_contract_smoke_test.tscn"
    ).read_text(encoding="utf-8")

    for socket_name in avatar_socket_names():
        assert socket_name in contract

    assert 'const BODY_SLIM := "slim"' in contract
    assert 'const BODY_STANDARD := "standard"' in contract
    assert 'const BODY_CHUBBY := "chubby"' in contract
    assert 'const ANIMATION_IDLE := "Idle"' in contract
    assert 'const ANIMATION_WALK := "Walk"' in contract
    assert 'const ANIMATION_RUN := "Run"' in contract

    assert "_probe_local_kaykit_animation_pack" in preview
    assert "Rig_Medium skeleton bones" in preview
    assert 'for semantic_name in ["Idle", "Walk", "Run"]' in preview
    assert '" mapping = "' in preview
    assert "locomotion contract" in preview
    assert "avatar_contract_preview.gd" in scene


def test_avatar_contract_documentation_exists():
    doc = (
        ROOT / "docs" / "AVATAR_CONTRACT_V1.md"
    ).read_text(encoding="utf-8")

    assert "humanoid_kaykit_v1" in doc
    assert "Slim" in doc
    assert "Standard" in doc
    assert "Chubby" in doc
    assert "KayKit Character Animations" in doc
    assert "Issue should stay open" not in doc



def test_custom_avatar_survives_sqlite_restart_and_matches_runtime(tmp_path):
    db_path = tmp_path / "studio.db"
    storage_path = tmp_path / "storage"
    repo = SQLiteStudioRepository(db_path)
    appearance = AvatarAppearance(
        customized=True,
        body_type=BodyType.CHUBBY,
        species_head_id="species_head_cat_v1",
        surface_type="fur",
        surface_color_hex="#F7B7D2",
        eye_style_id="eyes_cat_v1",
        eye_color_hex="#BDE3F5",
        hair_style_id="hair_ponytail_v1",
        hair_color_hex="#5B4036",
        compatible_tags=["humanoid", "species_head_cat_v1", "fur"],
    )
    profile = CharacterProfile(
        character_type="动物 / Animal",
        age="8",
        appearance="Cat hero",
        personality_traits=["勇敢 / Brave"],
        speaking_tone="轻快 / Bright",
        native_language="中文 / Chinese",
        english_level=5,
        avatar=appearance,
    )

    saved = AssetService(repo).create_character(
        name="Mimi",
        description="A brave cat hero.",
        profile=profile,
    )

    restarted = SQLiteStudioRepository(db_path)
    loaded = restarted.get_asset(saved.asset_id)
    assert loaded is not None

    restored_profile = CharacterProfile.model_validate(
        loaded.metadata["character_profile"]
    )
    assert restored_profile.avatar == appearance

    runtime = CharacterRuntimeService(
        restarted,
        LocalObjectStorage(storage_path),
    ).resolve(loaded)

    assert runtime.rig_family == appearance.rig_family
    assert runtime.body_type == BodyType.CHUBBY
    assert runtime.species_head_id == "species_head_cat_v1"
    assert runtime.surface_type == "fur"
    assert runtime.surface_color_hex == "#F7B7D2"
    assert runtime.eye_style_id == "eyes_cat_v1"
    assert runtime.eye_color_hex == "#BDE3F5"
    assert runtime.hair_style_id == "hair_ponytail_v1"
    assert runtime.hair_color_hex == "#5B4036"
    assert runtime.socket_names == avatar_socket_names()
