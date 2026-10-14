extends SceneTree

## One owner-scoped canonical Character + EquipmentRuntimeSpec must produce
## the same visible clothes/props in the playable village and Director.

func _initialize() -> void:
    var selection := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if selection == null:
        _fail("FamilySceneState is missing")
        return
    selection.clear_selection()
    var character := {
        "schema_version": "1.0",
        "character_id": "CHAR_TEST_OUTFIT_LILY",
        "display_name": "Lily",
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "body_type": "standard",
            "species_head_id": "species_head_sheep_v1",
            "surface_color_hex": "#F7B7D2"
        }}
    }
    var equipment := {
        "character_asset_id": "CHAR_TEST_OUTFIT_LILY",
        "final_stats": {"hp": 110, "atk": 16, "defense": 10},
        "equipped": {
            "top": {"item_instance_id": "ITEM_TOP_LILY", "rarity": "purple", "display_name": "Star Top"},
            "headwear": {"item_instance_id": "ITEM_CROWN_LILY", "rarity": "gold", "display_name": "Tiny Crown"},
            "weapon_main": {"item_instance_id": "ITEM_SWORD_LILY", "rarity": "blue", "display_name": "Star Sword"}
        }
    }

    if not selection.select_character(character):
        _fail("valid saved Hero rejected")
        return
    if selection.select_equipment({
        "character_asset_id": "CHAR_ANOTHER_CHILD",
        "final_stats": {},
        "equipped": equipment["equipped"]
    }):
        _fail("cross-profile equipment was accepted")
        return
    if not selection.select_equipment(equipment):
        _fail("own canonical equipment was rejected")
        return
    var payload := selection.active_play_session()
    if payload.get("equipment", {}).get("equipped", {}).size() != 3:
        _fail("canonical outfit and props did not reach the shared play format")
        return

    var packed := load("res://scenes/player.tscn") as PackedScene
    if packed == null:
        _fail("playable Hero scene missing")
        return
    var hero := packed.instantiate() as CharacterBody3D
    root.add_child(hero)
    await process_frame

    var sword := hero.find_child("Equipment_weapon_main", true, false) as Node3D
    var crown := hero.find_child("Equipment_headwear", true, false) as Node3D
    if sword == null or crown == null:
        _fail("game lost saved sword or crown")
        return
    var body := hero.get_node("Visual/Body") as MeshInstance3D
    var body_mat := body.material_override as StandardMaterial3D
    if body_mat == null or body_mat.albedo_color.to_html(false) != "b79ced":
        _fail("game lost saved purple top")
        return

    var director := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(director)
    director.configure({
        "director_session_id": "DIR_OUTFIT_TEST",
        "shot_id": "SHOT_01",
        "scene_id": "SCENE_01",
        "duration_seconds": 1.0,
        "play_session": payload,
        "camera": {"position": [0.0, 4.2, 7.8], "look_at": [0.0, 1.1, 0.0]},
        "shot": {}
    })
    await process_frame

    var film_sword := director.actor.find_child("Equipment_weapon_main", true, false) as Node3D
    var film_crown := director.actor.find_child("Equipment_headwear", true, false) as Node3D
    if film_sword == null or film_crown == null:
        _fail("film lost same saved sword or crown")
        return
    var film_body := director.actor.get_node("Visual/Body") as MeshInstance3D
    var film_mat := film_body.material_override as StandardMaterial3D
    if film_mat == null or film_mat.albedo_color.to_html(false) != "b79ced":
        _fail("film lost purple top from the shared Character")
        return

    if not selection.select_character({
        "schema_version": "1.0", "character_id": "CHAR_TEST_OTHER_CHILD",
        "profile": {"avatar": {"rig_family": MiniUtopiaAvatarContract.RIG_FAMILY}}
    }):
        _fail("second child selection failed")
        return
    if selection.active_play_session().get("equipment", {}).get("equipped", {}).size() != 0:
        _fail("outfit leaked when switching child Heroes")
        return

    selection.clear_selection()
    print("family_outfit_game_director_smoke: PASS · same top/sword/crown in game and film")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_outfit_game_director_smoke: FAIL · " + message)
    quit(1)
