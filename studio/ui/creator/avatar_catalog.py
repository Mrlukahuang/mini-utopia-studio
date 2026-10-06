from __future__ import annotations

from dataclasses import dataclass

from studio.models.avatar import BodyType


@dataclass(frozen=True)
class AvatarOption:
    option_id: str
    label: str
    tags: tuple[str, ...] = ()


BODY_TYPE_OPTIONS = (
    (BodyType.SLIM, "Slim / 偏瘦"),
    (BodyType.STANDARD, "Standard / 标准"),
    (BodyType.CHUBBY, "Chubby / 圆润"),
)

SPECIES_HEAD_OPTIONS = (
    AvatarOption("species_head_human_v1", "Human / 人类", ("skin", "hair")),
    AvatarOption("species_head_sheep_v1", "Sheep / 小羊", ("wool", "hair_optional")),
    AvatarOption("species_head_robot_v1", "Robot / 机器人", ("metal", "hair_optional")),
    AvatarOption("species_head_cat_v1", "Cat / 猫咪", ("fur", "hair_optional")),
    AvatarOption("species_head_cloud_v1", "Cloud Creature / 云朵生物", ("cloud", "hair_optional")),
)

SURFACE_OPTIONS = (
    AvatarOption("skin", "Skin / 皮肤"),
    AvatarOption("fur", "Fur / 毛发"),
    AvatarOption("wool", "Wool / 羊毛"),
    AvatarOption("metal", "Metal / 金属"),
    AvatarOption("cloud", "Cloud-soft / 云朵质感"),
)

EYE_STYLE_OPTIONS = (
    AvatarOption("eyes_round_soft_v1", "Round Soft / 圆圆软萌"),
    AvatarOption("eyes_sparkle_v1", "Sparkle / 闪亮大眼"),
    AvatarOption("eyes_sleepy_v1", "Sleepy / 困困眼"),
    AvatarOption("eyes_robot_v1", "Robot Screen / 机器人屏幕眼"),
    AvatarOption("eyes_cat_v1", "Cat / 猫眼"),
)

HAIR_STYLE_OPTIONS = (
    AvatarOption("hair_none", "None / 无"),
    AvatarOption("hair_short_v1", "Short / 短发"),
    AvatarOption("hair_bob_v1", "Bob / 波波头"),
    AvatarOption("hair_long_wavy_v1", "Long Wavy / 长卷发"),
    AvatarOption("hair_ponytail_v1", "Ponytail / 马尾"),
    AvatarOption("hair_fluffy_v1", "Fluffy / 蓬蓬头"),
)

AVATAR_COLOR_OPTIONS = {
    "Cream / 奶油白": "#F6F1E8",
    "Warm Skin / 暖肤色": "#F2C7A5",
    "Tan / 小麦色": "#C98E68",
    "Soft Brown / 浅棕": "#9A7657",
    "Dark Brown / 深棕": "#5B4036",
    "Soft Black / 柔黑": "#393A46",
    "Strawberry Pink / 草莓粉": "#F7B7D2",
    "Mint / 薄荷绿": "#B9E7D0",
    "Lavender / 薰衣草紫": "#D7C2F3",
    "Sky Blue / 天空蓝": "#BDE3F5",
    "Peach / 桃子色": "#F5C1B8",
    "Golden / 金黄色": "#F2C75C",
    "Pearl Metal / 珠白金属": "#E8ECEF",
    "Robot Blue / 机器人蓝": "#A9CFE8",
}


def option_label(options: tuple[AvatarOption, ...], option_id: str) -> str:
    for option in options:
        if option.option_id == option_id:
            return option.label
    return option_id


def option_ids(options: tuple[AvatarOption, ...]) -> list[str]:
    return [option.option_id for option in options]


def species_default_surface(species_head_id: str) -> str:
    mapping = {
        "species_head_human_v1": "skin",
        "species_head_sheep_v1": "wool",
        "species_head_robot_v1": "metal",
        "species_head_cat_v1": "fur",
        "species_head_cloud_v1": "cloud",
    }
    return mapping.get(species_head_id, "skin")


def allowed_surface_ids(species_head_id: str) -> tuple[str, ...]:
    mapping = {
        "species_head_human_v1": ("skin",),
        "species_head_sheep_v1": ("wool", "fur"),
        "species_head_robot_v1": ("metal",),
        "species_head_cat_v1": ("fur",),
        "species_head_cloud_v1": ("cloud",),
    }
    return mapping.get(species_head_id, ("skin",))


def allowed_eye_ids(species_head_id: str) -> tuple[str, ...]:
    if species_head_id == "species_head_robot_v1":
        return ("eyes_robot_v1", "eyes_round_soft_v1")
    if species_head_id == "species_head_cat_v1":
        return ("eyes_cat_v1", "eyes_round_soft_v1", "eyes_sparkle_v1")
    return (
        "eyes_round_soft_v1",
        "eyes_sparkle_v1",
        "eyes_sleepy_v1",
    )


def allowed_hair_ids(species_head_id: str) -> tuple[str, ...]:
    if species_head_id in {"species_head_robot_v1", "species_head_cloud_v1"}:
        return ("hair_none", "hair_short_v1", "hair_fluffy_v1")
    return tuple(option.option_id for option in HAIR_STYLE_OPTIONS)
