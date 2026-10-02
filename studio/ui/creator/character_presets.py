from __future__ import annotations

CUSTOM = "自定义 / Custom"

CHARACTER_TYPE_OPTIONS = [
    "人类 / Human",
    "动物 / Animal",
    "机器人 / Robot",
    "奇幻生物 / Fantasy Creature",
    "精灵 / Spirit",
    "外星生物 / Alien",
    "玩具角色 / Toy Character",
    "植物生物 / Plant Creature",
    "交通工具角色 / Vehicle Character",
    CUSTOM,
]

STORY_ROLE_OPTIONS = [
    "旅行者 / Traveler",
    "探险家 / Explorer",
    "发明家 / Inventor",
    "守护者 / Guardian",
    "伙伴 / Friend",
    "向导 / Guide",
    "收藏家 / Collector",
    "梦想家 / Dreamer",
    "科学家 / Scientist",
    "艺术家 / Artist",
    "信使 / Messenger",
    "神秘角色 / Mystery Role",
    CUSTOM,
]

AGE_OPTIONS = ["4","5","6","7","8","9","10","11","12","Teen / 青少年","Adult / 成年","Ageless / 无年龄",CUSTOM]

BODY_BUILD_OPTIONS = [
    "很瘦 / Very slim","偏瘦 / Slim","普通 / Average",
    "圆润 / Round","胖胖的 / Chubby","壮壮的 / Strong",CUSTOM,
]

HEIGHT_OPTIONS = [
    "很矮 / Very short","偏矮 / Short","中等 / Medium",
    "偏高 / Tall","很高 / Very tall",CUSTOM,
]

FACE_STYLE_OPTIONS = [
    "超可爱 / Very cute","甜美 / Sweet","好奇 / Curious","温柔 / Gentle",
    "调皮 / Mischievous","勇敢 / Brave","安静 / Calm","困困的 / Sleepy",CUSTOM,
]

HAIR_FUR_KIND_OPTIONS = ["头发 / Hair","毛发 / Fur","头发和毛发 / Both","没有 / None",CUSTOM]

HAIR_FUR_TEXTURE_OPTIONS = [
    "柔软 / Soft","蓬松 / Fluffy","卷卷的 / Curly","波浪 / Wavy",
    "顺直 / Straight","羊毛感 / Woolly","尖尖的 / Spiky",
    "云朵感 / Cloud-like","叶片感 / Leaf-like","光滑玩具表面 / Smooth toy surface",CUSTOM,
]

HAIRSTYLE_OPTIONS = [
    "短发 / Short hair","波波头 / Bob","长直发 / Long straight","长卷发 / Long curly",
    "高马尾 / High ponytail","低马尾 / Low ponytail","双马尾 / Pigtails",
    "丸子头 / Bun","双丸子头 / Double buns","单辫 / Single braid",
    "双辫 / Twin braids","半扎发 / Half-up","精灵短发 / Pixie cut",
    "蓬蓬圆圆 / Fluffy round","不适用 / N/A",CUSTOM,
]

EYE_SHAPE_OPTIONS = [
    "大而圆 / Large round","大而闪亮 / Big sparkling","杏仁眼 / Almond",
    "下垂无辜眼 / Droopy","星星眼 / Starry","扣子眼 / Button eyes",
    "屏幕眼 / Robot screen eyes",CUSTOM,
]

COLOR_PRESETS = {
    "奶油白 / Cream White": "#F6F1E8",
    "金色 / Blonde": "#E9C989",
    "浅棕 / Light Brown": "#9A7657",
    "深棕 / Dark Brown": "#5B4036",
    "柔黑 / Soft Black": "#393A46",
    "草莓粉 / Strawberry Pink": "#F7B7D2",
    "薄荷绿 / Mint": "#B9E7D0",
    "Tiffany Blue": "#81D8D0",
    "薰衣草紫 / Lavender": "#D7C2F3",
    "桃子色 / Peach": "#F5C1B8",
    "天空蓝 / Sky Blue": "#BDE3F5",
    "金黄色 / Golden Yellow": "#F2C75C",
    CUSTOM: "",
}
