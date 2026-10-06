from pathlib import Path

from studio.models.avatar import AvatarAppearance, BodyType
from studio.models.character import CharacterProfile
from studio.ui.creator.avatar_legacy_bridge import legacy_visual_updates


ROOT = Path(__file__).resolve().parents[1]


def test_avatar_is_single_source_for_legacy_visual_fields():
    profile = CharacterProfile(
        character_type="人类 / Human",
        appearance="",
    )
    avatar = AvatarAppearance(
        customized=True,
        body_type=BodyType.CHUBBY,
        species_head_id="species_head_sheep_v1",
        surface_type="wool",
        surface_color_hex="#F6F1E8",
        eye_style_id="eyes_sparkle_v1",
        eye_color_hex="#BDE3F5",
        hair_style_id="hair_bob_v1",
        hair_color_hex="#F7B7D2",
    )

    updates = legacy_visual_updates(profile, avatar)

    assert updates["avatar"] == avatar
    assert updates["character_type"] == "动物 / Animal"
    assert updates["body_build"] == "圆润 / Chubby"
    assert updates["body_type"] == "圆润 / Chubby"
    assert updates["hair_or_fur"] == "头发和毛发 / Both"
    assert updates["skin_fur_material"] == "羊毛感 / Woolly"
    assert updates["hair_style"] == "波波头 / Bob"
    assert updates["hair_or_fur_color_hex"] == "#F7B7D2"
    assert updates["eyes"].shape == "大而闪亮 / Big sparkling"
    assert updates["eyes"].color_hex == "#BDE3F5"


def test_character_factory_does_not_ask_duplicate_visual_questions():
    factory = (
        ROOT / "studio" / "ui" / "creator" / "character_factory.py"
    ).read_text(encoding="utf-8")

    duplicate_labels = (
        "Character Type / 角色类型",
        "Hair or Fur / 头发或毛发",
        "Texture / 质感",
        "Hairstyle / 发型",
        "Hair / Fur Color / 头发毛发颜色",
        "Eye Shape / 眼睛形状",
    )
    for label in duplicate_labels:
        assert label not in factory

    assert "Story Visual Details / 故事视觉细节" in factory
    assert "Favorite Colors / 最喜欢的颜色" in factory
    assert "Distinctive Feature / 特别特征" in factory
    assert "legacy_visual_updates(draft, avatar)" in factory


def test_factory_preview_is_large_real_3d_and_reusable():
    editor = (
        ROOT / "studio" / "ui" / "creator" / "avatar_editor.py"
    ).read_text(encoding="utf-8")
    preview = (
        ROOT / "studio" / "ui" / "creator" / "avatar_preview.py"
    ).read_text(encoding="utf-8")
    runtime = (
        ROOT / "studio" / "runtime" / "avatar_preview_3d.py"
    ).read_text(encoding="utf-8")

    assert 'st.columns([0.86, 1.74], gap="large")' in editor
    assert "Live 3D Avatar / 实时 3D 预览" in preview
    assert "components.html(" in preview
    assert "height: int = 620" in preview
    assert "height=height" in preview
    assert "THREE.WebGLRenderer" in runtime
    assert "OrbitControls" in runtime
    assert "avatar-stage" not in preview
