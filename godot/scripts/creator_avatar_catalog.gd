class_name MiniUtopiaCreatorAvatarCatalog
extends RefCounted

const BODY_OPTIONS := {
    "slim": "Slim",
    "standard": "Standard",
    "chubby": "Chubby",
}

const SPECIES_OPTIONS := {
    "species_head_human_v1": "Human",
    "species_head_sheep_v1": "Sheep",
    "species_head_robot_v1": "Robot",
    "species_head_cat_v1": "Cat",
    "species_head_cloud_v1": "Cloud",
}

const SURFACE_OPTIONS := {
    "skin": "Skin",
    "fur": "Fur",
    "wool": "Wool",
    "metal": "Metal",
    "cloud": "Cloud",
}

const EYE_OPTIONS := {
    "eyes_round_soft_v1": "Round",
    "eyes_sparkle_v1": "Sparkle",
    "eyes_sleepy_v1": "Sleepy",
    "eyes_robot_v1": "Robot",
    "eyes_cat_v1": "Cat",
}

const HAIR_OPTIONS := {
    "hair_none": "None",
    "hair_short_v1": "Short",
    "hair_bob_v1": "Bob",
    "hair_long_wavy_v1": "Long",
    "hair_ponytail_v1": "Ponytail",
    "hair_fluffy_v1": "Fluffy",
}

const COLOR_OPTIONS := {
    "Cream": "#F6F1E8",
    "Warm": "#F2C7A5",
    "Tan": "#C98E68",
    "Brown": "#9A7657",
    "Dark": "#5B4036",
    "Black": "#393A46",
    "Pink": "#F7B7D2",
    "Mint": "#B9E7D0",
    "Lavender": "#D7C2F3",
    "Sky": "#BDE3F5",
    "Peach": "#F5C1B8",
    "Gold": "#F2C75C",
    "Pearl": "#E8ECEF",
    "Robot Blue": "#A9CFE8",
}


static func species_default_surface(species_head_id: String) -> String:
    match species_head_id:
        "species_head_sheep_v1":
            return "wool"
        "species_head_robot_v1":
            return "metal"
        "species_head_cat_v1":
            return "fur"
        "species_head_cloud_v1":
            return "cloud"
        _:
            return "skin"


static func allowed_surface_ids(species_head_id: String) -> Array[String]:
    match species_head_id:
        "species_head_sheep_v1":
            return ["wool", "fur"]
        "species_head_robot_v1":
            return ["metal"]
        "species_head_cat_v1":
            return ["fur"]
        "species_head_cloud_v1":
            return ["cloud"]
        _:
            return ["skin"]


static func allowed_eye_ids(species_head_id: String) -> Array[String]:
    if species_head_id == "species_head_robot_v1":
        return ["eyes_robot_v1", "eyes_round_soft_v1"]
    if species_head_id == "species_head_cat_v1":
        return [
            "eyes_cat_v1",
            "eyes_round_soft_v1",
            "eyes_sparkle_v1",
        ]
    return [
        "eyes_round_soft_v1",
        "eyes_sparkle_v1",
        "eyes_sleepy_v1",
    ]


static func allowed_hair_ids(species_head_id: String) -> Array[String]:
    if (
        species_head_id == "species_head_robot_v1"
        or species_head_id == "species_head_cloud_v1"
    ):
        return ["hair_none", "hair_short_v1", "hair_fluffy_v1"]
    return [
        "hair_none",
        "hair_short_v1",
        "hair_bob_v1",
        "hair_long_wavy_v1",
        "hair_ponytail_v1",
        "hair_fluffy_v1",
    ]
