extends SceneTree

func _initialize() -> void:
    var state := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    state.clear_selection()
    var hero := {"schema_version":"1.0","character_id":"CHAR_CRAFT_TEST",
        "display_name":"Sheep","profile":{"avatar":{
        "rig_family":MiniUtopiaAvatarContract.RIG_FAMILY}}}
    var gear := {"character_asset_id":"CHAR_CRAFT_TEST","final_stats":{},
        "equipped":{"weapon_main":{"item_instance_id":"ITEM_CRAFT_TEST",
        "display_name":"Star Wand","rarity":"green",
        "visual_recipe":{"schema_version":"1.0","shape":"star",
        "color_hex":"#B9E7D0","accent_color_hex":"#F2C75C"}}}}
    if not state.select_character(hero) or not state.select_equipment(gear):
        _fail("canonical hero/gear rejected")
        return
    var packed := load("res://scenes/player.tscn") as PackedScene
    var player := packed.instantiate() as CharacterBody3D
    root.add_child(player)
    await process_frame
    if not _has_star(player):
        _fail("game has no crafted wand")
        return
    var stage := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(stage)
    stage.configure({"director_session_id":"DIR_CRAFT_TEST","shot_id":"SHOT1",
        "scene_id":"SCENE1","duration_seconds":1.0,
        "play_session":state.active_play_session(),
        "camera":{"position":[0,4,8],"look_at":[0,1,0]},"shot":{}})
    await process_frame
    if stage.actor == null or not _has_star(stage.actor):
        _fail("Director lost crafted wand")
        return
    if stage.play_runtime.payload.get("equipment", {}).get("equipped", {}
        ).get("weapon_main", {}).get("item_instance_id") != "ITEM_CRAFT_TEST":
        _fail("Director invented a different item")
        return
    state.clear_selection()
    print("family_crafted_prop_game_director_smoke: PASS")
    quit(0)

func _has_star(actor: CharacterBody3D) -> bool:
    var prop := actor.find_child("Equipment_weapon_main", true, false)
    if prop == null:
        return false
    var core := prop.get_node_or_null("CraftedCore") as MeshInstance3D
    var tip := prop.get_node_or_null("StarTip0") as MeshInstance3D
    if core == null or tip == null:
        return false
    var main_mat := core.material_override as StandardMaterial3D
    var tip_mat := tip.material_override as StandardMaterial3D
    return main_mat != null and tip_mat != null and (
        main_mat.albedo_color.to_html(false) == "b9e7d0"
        and tip_mat.albedo_color.to_html(false) == "f2c75c")

func _fail(message: String) -> void:
    push_error("family_crafted_prop_game_director_smoke: FAIL " + message)
    quit(1)
