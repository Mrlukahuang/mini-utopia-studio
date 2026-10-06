from __future__ import annotations

from studio.models.avatar import AvatarAppearance
from studio.models.character import CharacterProfile
from studio.ui.creator.avatar_catalog import AVATAR_COLOR_OPTIONS
from studio.ui.creator.character_presets import COLOR_PRESETS


_BODY_BUILD = {
    "slim": "偏瘦 / Slim",
    "standard": "普通 / Standard",
    "chubby": "圆润 / Chubby",
}

_CHARACTER_TYPE = {
    "species_head_human_v1": "人类 / Human",
    "species_head_sheep_v1": "动物 / Animal",
    "species_head_cat_v1": "动物 / Animal",
    "species_head_robot_v1": "机器人 / Robot",
    "species_head_cloud_v1": "云朵生物 / Cloud Creature",
}

_HAIR_STYLE = {
    "hair_none": "不适用 / N/A",
    "hair_short_v1": "短发 / Short hair",
    "hair_bob_v1": "波波头 / Bob",
    "hair_long_wavy_v1": "长卷发 / Long curly",
    "hair_ponytail_v1": "高马尾 / High ponytail",
    "hair_fluffy_v1": "蓬蓬圆圆 / Fluffy round",
}

_EYE_SHAPE = {
    "eyes_round_soft_v1": "大而圆 / Large round",
    "eyes_sparkle_v1": "大而闪亮 / Big sparkling",
    "eyes_sleepy_v1": "下垂无辜眼 / Droopy",
    "eyes_robot_v1": "屏幕眼 / Robot screen eyes",
    "eyes_cat_v1": "杏仁眼 / Almond",
}

_SURFACE_TEXTURE = {
    "skin": "光滑玩具表面 / Smooth toy surface",
    "fur": "柔软 / Soft",
    "wool": "羊毛感 / Woolly",
    "metal": "光滑玩具表面 / Smooth toy surface",
    "cloud": "云朵感 / Cloud-like",
}


def _legacy_color_label(hex_value: str) -> str:
    normalized = (hex_value or "").lower()
    for label, value in COLOR_PRESETS.items():
        if value and value.lower() == normalized:
            return label
    for label, value in AVATAR_COLOR_OPTIONS.items():
        if value.lower() == normalized:
            return label
    return "自定义 / Custom"


def _hair_kind(avatar: AvatarAppearance) -> str:
    has_hair = avatar.hair_style_id != "hair_none"
    has_surface_hair = avatar.surface_type in {"fur", "wool"}
    if has_hair and has_surface_hair:
        return "头发和毛发 / Both"
    if has_hair:
        return "头发 / Hair"
    if has_surface_hair:
        return "毛发 / Fur"
    return "没有 / None"


def legacy_visual_updates(
    profile: CharacterProfile,
    avatar: AvatarAppearance,
) -> dict:
    """Derive legacy CharacterProfile visuals from the canonical AvatarAppearance.

    Old fields stay populated for existing story/master-image consumers, but the
    child only edits the AvatarAppearance controls.
    """

    hair_color = _legacy_color_label(avatar.hair_color_hex)
    eye_color = _legacy_color_label(avatar.eye_color_hex)

    return {
        "avatar": avatar,
        "character_type": _CHARACTER_TYPE.get(
            avatar.species_head_id,
            profile.character_type,
        ),
        "body_build": _BODY_BUILD[avatar.body_type.value],
        "body_type": _BODY_BUILD[avatar.body_type.value],
        "hair_or_fur": _hair_kind(avatar),
        "skin_fur_material": _SURFACE_TEXTURE.get(
            avatar.surface_type,
            profile.skin_fur_material,
        ),
        "hair_style": _HAIR_STYLE.get(
            avatar.hair_style_id,
            profile.hair_style,
        ),
        "hair_or_fur_color": hair_color,
        "hair_or_fur_color_hex": avatar.hair_color_hex,
        "eyes": profile.eyes.model_copy(
            update={
                "shape": _EYE_SHAPE.get(
                    avatar.eye_style_id,
                    profile.eyes.shape,
                ),
                "color": eye_color,
                "color_hex": avatar.eye_color_hex,
            }
        ),
        "appearance": (
            profile.appearance
            or "cute Mini Utopia playable avatar with clean block-built toy forms"
        ),
    }
