extends SceneTree

## Two synthetic characters previously fetched through ONE child's private
## Family API session. They must keep different stable IDs, colors and gear.

func _initialize() -> void:
    var lily := _play(
        "CHAR_SAME_OWNER_LILY", "#F7B7D2", "ITEM_LILY_CROWN", "gold"
    )
    var mia := _play(
        "CHAR_SAME_OWNER_MIA", "#B9E7D0", "ITEM_MIA_CROWN", "purple"
    )
    if not MiniUtopiaFamilyDirectorSession.from_two_play_sessions(
        lily, lily
    ).is_empty():
        _fail("duplicate Character ID was accepted twice")
        return

    var invalid := mia.duplicate(true)
    invalid["source"] = "unverified_public_character"
    if not MiniUtopiaFamilyDirectorSession.from_two_play_sessions(
        lily, invalid
    ).is_empty():
        _fail("unsupported public guest was accepted as family cast")
        return

    var session := MiniUtopiaFamilyDirectorSession.from_two_play_sessions(
        lily, mia
    )
    if session.is_empty():
        _fail("valid two-character shot was rejected")
        return
    if session.get("shot", {}).get("asset_ids", []).size() != 3:
        _fail("shot lost one or both canonical cast IDs")
        return
    if session.get("duration_seconds") != 15.0:
        _fail("two-character shot must remain 15 seconds")
        return

    var runtime := MiniUtopiaDirectorShotRuntime.new()
    runtime.name = "TwoHeroesTestRuntime"
    root.add_child(runtime)
    runtime.configure(session)
    await process_frame

    if runtime.actor == null or runtime.second_actor == null:
        _fail("both characters did not render in one Director stage")
        return
    if runtime.actor.get_meta("mini_utopia_character_asset_id", "") != "CHAR_SAME_OWNER_LILY":
        _fail("first actor lost canonical Character ID")
        return
    if runtime.second_actor.get_meta("mini_utopia_character_asset_id", "") != "CHAR_SAME_OWNER_MIA":
        _fail("second actor lost canonical Character ID")
        return
    var first_head := runtime.actor.get_node("Visual/Head") as MeshInstance3D
    var second_head := runtime.second_actor.get_node("Visual/Head") as MeshInstance3D
    var first_mat := first_head.material_override as StandardMaterial3D
    var second_mat := second_head.material_override as StandardMaterial3D
    if first_mat == null or second_mat == null:
        _fail("canonical character surfaces missing")
        return
    if first_mat.albedo_color.to_html(false) != "f7b7d2":
        _fail("first actor's color changed")
        return
    if second_mat.albedo_color.to_html(false) != "b9e7d0":
        _fail("second actor's color changed")
        return

    var first_hat := runtime.actor.find_child("Equipment_headwear", true, false)
    var second_hat := runtime.second_actor.find_child(
        "Equipment_headwear", true, false
    )
    if first_hat == null or second_hat == null:
        _fail("both saved crowns must be visible together")
        return
    if (
        runtime.play_runtime.payload.get("equipment", {}).get(
            "equipped", {}
        ).get("headwear", {}).get("item_instance_id", "") != "ITEM_LILY_CROWN"
        or runtime.second_play_runtime.payload.get("equipment", {}).get(
            "equipped", {}
        ).get("headwear", {}).get("item_instance_id", "") != "ITEM_MIA_CROWN"
    ):
        _fail("the second actor inherited the first actor's equipment")
        return

    if not runtime.bound_world_loaded:
        _fail("two actors did not share the playable village")
        return
    var first_start := runtime.actor.position
    var second_start := runtime.second_actor.position
    if first_start.distance_to(second_start) < 1.5:
        _fail("the two actors overlap at scene start")
        return
    runtime.advance_shot(4.5)
    if runtime.elapsed_seconds < 4.0:
        _fail("15-second timeline did not advance")
        return
    if runtime.actor.position == first_start or runtime.second_actor.position == second_start:
        _fail("both actors should walk in the shared shot")
        return
    if runtime.performance_last_cue != "celebrate":
        _fail("timed performance cue was lost")
        return

    runtime.reset_shot()
    if runtime.actor.position != first_start or runtime.second_actor.position != second_start:
        _fail("Replay did not reset both actors")
        return
    if runtime.elapsed_seconds != 0.0 or not runtime.playing:
        _fail("Replay did not restart the shared timeline")
        return

    var single := MiniUtopiaFamilyDirectorSession.from_play_session(lily)
    runtime.configure(single)
    await process_frame
    if runtime.second_actor != null or runtime.second_play_runtime != null:
        _fail("a single-character shot kept a previous second actor")
        return

    print("family_two_heroes_director_smoke: PASS · two IDs, outfits, walk, replay")
    quit(0)


func _play(
    character_id: String,
    surface_color: String,
    item_id: String,
    rarity: String
) -> Dictionary:
    var saved := {
        "schema_version": "1.0",
        "character_id": character_id,
        "display_name": character_id,
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "species_head_id": "species_head_cat_v1",
            "surface_color_hex": surface_color,
            "hair_style_id": "hair_none",
        }}
    }
    var result := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(saved)
    result["equipment"] = {
        "equipped": {
            "headwear": {
                "item_instance_id": item_id,
                "display_name": "My Crown",
                "rarity": rarity,
            }
        },
        "final_stats": {"hp": 100, "atk": 10, "defense": 8},
    }
    return result


func _fail(message: String) -> void:
    push_error("family_two_heroes_director_smoke: FAIL · " + message)
    quit(1)
