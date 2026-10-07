extends SceneTree


func _initialize() -> void:
    var path := "res://config/runtime/bridge_character_example.json"
    var text := FileAccess.get_file_as_string(path)
    if text.is_empty():
        _fail("example Character contract is missing")
        return

    var payload = JSON.parse_string(text)
    if typeof(payload) != TYPE_DICTIONARY:
        _fail("Character contract is not a JSON object")
        return
    if payload.get("schema_version") != "1.0":
        _fail("Bridge Character schema version mismatch")
        return
    if payload.get("character_id") != "CHAR_BRIDGE_EXAMPLE":
        _fail("stable Character ID missing")
        return

    var profile = payload.get("profile")
    if typeof(profile) != TYPE_DICTIONARY:
        _fail("profile missing")
        return
    var avatar = profile.get("avatar")
    if typeof(avatar) != TYPE_DICTIONARY:
        _fail("profile.avatar missing")
        return

    var expected := {
        "rig_family": "humanoid_kaykit_v1",
        "body_type": "chubby",
        "species_head_id": "species_head_cat_v1",
        "surface_type": "fur",
        "surface_color_hex": "#F7B7D2",
        "eye_style_id": "eyes_cat_v1",
        "eye_color_hex": "#BDE3F5",
        "hair_style_id": "hair_ponytail_v1",
        "hair_color_hex": "#5B4036",
    }
    for key in expected:
        if avatar.get(key) != expected[key]:
            _fail("avatar field mismatch: %s" % key)
            return

    print("bridge_character_contract_smoke: PASS · Godot parsed CharacterProfile + AvatarAppearance")
    quit(0)


func _fail(message: String) -> void:
    push_error("bridge_character_contract_smoke: FAIL · %s" % message)
    quit(1)
