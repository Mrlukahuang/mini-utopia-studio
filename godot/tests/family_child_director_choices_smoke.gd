extends SceneTree

## Interactive controls must actually change a 15/30-second live shot, while
## retaining canonical character IDs and their individual outfits.

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        _fail("FamilySceneState autoload missing")
        return
    family.disconnect_family()
    family.select_character(_hero("CHAR_DIRECTOR_A", "#F7B7D2"))
    family.select_equipment(_gear("CHAR_DIRECTOR_A", "ITEM_A_CROWN"))
    # Two actors in one film, from already-authorized test snapshots.
    if not family.connect_family(
        "https://family.example",
        "synthetic_director_test_session_0123456789"
    ):
        _fail("scoped film session missing")
        return
    family.select_character(_hero("CHAR_DIRECTOR_A", "#F7B7D2"))
    family.select_equipment(_gear("CHAR_DIRECTOR_A", "ITEM_A_CROWN"))
    family.select_second_cast_character(_hero("CHAR_DIRECTOR_B", "#B9E7D0"))
    family.select_second_cast_equipment(_gear("CHAR_DIRECTOR_B", "ITEM_B_CROWN"))

    var stage = load("res://scenes/director_stage.tscn").instantiate()
    root.add_child(stage)
    await process_frame

    var controls := stage.get_node_or_null(
        "DirectorStageOverlay/KidDirectorChoices"
    ) as VBoxContainer
    if controls == null:
        _fail("child director controls missing")
        return
    for key in ["camera", "action", "duration_seconds"]:
        var button := controls.get_node_or_null("Choice_" + key) as Button
        if button == null or button.custom_minimum_size.y < 48:
            _fail("iPad director touch button missing or undersized: " + key)
            return
        if button.pressed.get_connections().is_empty():
            _fail("choice button not connected: " + key)
            return

    if stage.director_runtime.actor == null or stage.director_runtime.second_actor == null:
        _fail("two saved Heroes not staged")
        return
    stage._cycle_child_choice("camera")
    if family.director_shot_choices["camera"] != "wide":
        _fail("camera option did not advance")
        return
    if stage.director_runtime.camera_start_fov != 58.0:
        _fail("wide camera field of view not applied")
        return

    stage._cycle_child_choice("action")
    if stage.director_runtime.blocking_movement_style != "run":
        _fail("run action not applied to actor path")
        return
    stage._cycle_child_choice("duration_seconds")
    if stage.director_runtime.duration_seconds != 30.0:
        _fail("30-second timeline not applied to runtime")
        return
    if family.director_shot_choices["duration_seconds"] != 30:
        _fail("child film length not retained across restage")
        return
    if stage.director_runtime.actor.get_meta(
        "mini_utopia_character_asset_id", ""
    ) != "CHAR_DIRECTOR_A":
        _fail("camera choice replaced first saved Hero")
        return
    if stage.director_runtime.second_actor.get_meta(
        "mini_utopia_character_asset_id", ""
    ) != "CHAR_DIRECTOR_B":
        _fail("camera choice replaced second saved Hero")
        return
    if stage.director_runtime.second_play_runtime.payload.get(
        "equipment", {}
    ).get("equipped", {}).get("headwear", {}).get(
        "item_instance_id"
    ) != "ITEM_B_CROWN":
        _fail("film editing lost second Hero wardrobe")
        return
    stage._cycle_child_choice("action")
    if stage.director_runtime.blocking_movement_style != "hold":
        _fail("celebrate action should hold actor position")
        return
    stage.director_runtime.advance_shot(8.2)
    if stage.director_runtime.performance_last_cue != "celebrate":
        _fail("30-second timeline did not retime performance cues")
        return
    stage._on_replay_pressed()
    if stage.director_runtime.elapsed_seconds != 0.0:
        _fail("Replay did not reset edited shot")
        return

    family.disconnect_family()
    if family.director_shot_choices["duration_seconds"] != 15:
        _fail("child choices leaked to the next profile after logout")
        return

    print("family_child_director_choices_smoke: PASS · 2 Heroes, camera, action, 30s")
    quit(0)


func _hero(cid: String, tint: String) -> Dictionary:
    return {
        "schema_version": "1.0", "character_id": cid, "display_name": cid,
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "surface_color_hex": tint,
            "species_head_id": "species_head_cat_v1",
        }}
    }


func _gear(cid: String, item: String) -> Dictionary:
    return {
        "character_asset_id": cid,
        "equipped": {"headwear": {
            "item_instance_id": item, "display_name": "My Crown",
            "rarity": "gold"
        }},
        "final_stats": {}
    }


func _fail(message: String) -> void:
    push_error("family_child_director_choices_smoke: FAIL · " + message)
    quit(1)
