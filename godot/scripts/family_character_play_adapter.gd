class_name MiniUtopiaFamilyCharacterPlayAdapter
extends RefCounted

## Converts ONE canonical Python Character contract to the existing shared
## CreatorPlayRuntime format. Used by the game and the Director; never
## generates a duplicate Character ID, appearance store, or replacement mesh.


static func play_session_for(contract: Dictionary) -> Dictionary:
    if String(contract.get("schema_version", "")) != "1.0":
        return {}
    var character_id := String(contract.get("character_id", ""))
    if not character_id.begins_with("CHAR_") or character_id.length() < 8:
        return {}
    var profile = contract.get("profile", {})
    if typeof(profile) != TYPE_DICTIONARY:
        return {}
    var avatar = profile.get("avatar", {})
    if typeof(avatar) != TYPE_DICTIONARY:
        return {}

    var appearance: Dictionary = avatar.duplicate(true)
    if String(appearance.get("rig_family", MiniUtopiaAvatarContract.RIG_FAMILY)) != MiniUtopiaAvatarContract.RIG_FAMILY:
        return {}

    var surface_color := String(appearance.get("surface_color_hex", "#F2C7A5"))
    var character := {
        "mode": "procedural",
        "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
        "body_type": String(appearance.get("body_type", "standard")),
        "species_head_id": String(appearance.get("species_head_id", "species_head_human_v1")),
        "surface_type": String(appearance.get("surface_type", "skin")),
        "surface_color_hex": surface_color,
        "body_color_hex": surface_color,
        "eye_style_id": String(appearance.get("eye_style_id", "eyes_round_soft_v1")),
        "eye_color_hex": String(appearance.get("eye_color_hex", "#7A5238")),
        "hair_style_id": String(appearance.get("hair_style_id", "hair_none")),
        "hair_color_hex": String(appearance.get("hair_color_hex", "#5B4036")),
    }
    return {
        "schema_version": "1.0",
        "session_id": "PLAY_FAMILY_" + character_id,
        "source": "family_character",
        "character_asset_id": character_id,
        "character_name": String(contract.get("display_name", character_id)),
        "character": character,
        # Equipment is fetched through an owner-scoped endpoint in a later
        # slice. Never invent owned items from client data.
        "equipment": {"equipped": {}, "final_stats": {}},
        "world_asset_id": "LOC_NEWBIE_VILLAGE",
        "world_name": "Newbie Village",
    }
