extends SceneTree

const TOKEN := "synthetic_film_reopen_child_0123456789abcdefghijkl"
const FILM_ID := "FILM_SAVED_FAMILY_TEST"

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    family.disconnect_family()
    var library := (load("res://scenes/family_hero_library.tscn") as PackedScene).instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame

    var original := library.bridge
    library.remove_child(original)
    original.free()
    var stub = (load("res://tests/film_restore_stub.gd") as GDScript).new()
    stub.name = "FilmBridgeStub"
    library.add_child(stub)
    library.bridge = stub

    if not family.connect_family("https://family.example", TOKEN, "child_a"):
        _fail("could not open synthetic child account")
        return
    if not family.bind_family_client(stub):
        _fail("stub could not bind private child token")
        return
    library._set_connected(true)
    if library.movies_button.disabled or library.movies_button.custom_minimum_size.y < 48:
        _fail("My Movies touch button is missing")
        return
    library._on_bridge_success("films:list", {
        "schema_version": "1.0", "films": [
            {"film_id": FILM_ID, "revision": "3", "draft": _draft()}
        ]
    })
    var saved_button := library.movie_list.get_node_or_null("Film_" + FILM_ID) as Button
    if saved_button == null or saved_button.custom_minimum_size.y < 48:
        _fail("saved film list has no touchable Continue button")
        return
    if saved_button.pressed.get_connections().is_empty():
        _fail("Continue is not wired")
        return

    library._on_saved_movie_pressed(FILM_ID)
    if stub.calls.back() != "films:get:" + FILM_ID:
        _fail("must reopen saved film from private server, not cached list")
        return
    library._on_bridge_success("films:get", _record())
    if stub.calls.back() != "character:get:CHAR_OWN_LILY":
        _fail("must recheck first saved Hero via owner-scoped GET")
        return
    # If the server refuses a no-longer-owned Hero, none of the previous
    # movie/character state is allowed to enter the Director.
    library._on_bridge_failure("character:get", 404, "not_found", "")
    if not family.opened_saved_film.is_empty() or not family.active_character.is_empty():
        _fail("404 actor leaked into saved film or active character")
        return
    if not library._movie_phase.is_empty():
        _fail("failed private restoration did not reset")
        return

    library._on_saved_movie_pressed(FILM_ID)
    library._on_bridge_success("films:get", _record())
    library._on_bridge_success("character:get", _hero("CHAR_OWN_LILY", "#F7B7D2"))
    if stub.calls.back() != "equipment:get:CHAR_OWN_LILY":
        _fail("must fetch first actor's CURRENT canonical wardrobe")
        return
    library._on_bridge_success("equipment:get", {
        "runtime": _gear("CHAR_OWN_LILY", "ITEM_SAVED_STAR")
    })
    if stub.calls.back() != "character:get:CHAR_OWN_CAT":
        _fail("must separately authorize second actor")
        return
    library._on_bridge_success("character:get", _hero("CHAR_OWN_CAT", "#B9E7D0"))
    if stub.calls.back() != "equipment:get:CHAR_OWN_CAT":
        _fail("must fetch second actor's current outfit")
        return
    library._on_bridge_success("equipment:get", {
        "runtime": _gear("CHAR_OWN_CAT", "ITEM_SAVED_CROWN")
    })
    if family.opened_saved_film.get("film_id", "") != FILM_ID:
        _fail("owned saved film not staged")
        return
    if family.director_shot_choices != {
        "action": "celebrate", "camera": "close", "duration_seconds": 30,
        "caption_preset": "hello"
    }:
        _fail("saved camera, movement or duration were lost")
        return
    if family.active_equipment.get("equipped", {}).get(
        "weapon_main", {}
    ).get("item_instance_id") != "ITEM_SAVED_STAR":
        _fail("first actor's saved prop was replaced")
        return
    if family.second_cast_equipment.get("equipped", {}).get(
        "headwear", {}
    ).get("item_instance_id") != "ITEM_SAVED_CROWN":
        _fail("second actor's own clothes were replaced")
        return

    await process_frame
    var scene = current_scene
    if scene == null or scene.saved_film_id != FILM_ID:
        _fail("film ID not passed to Director to edit, rather than duplicate")
        return
    if scene.saved_film_revision != "3":
        _fail("save revision not restored; next edit would conflict")
        return
    if scene.film_title_input.text != "Cloud Adventure":
        _fail("saved film title not restored")
        return
    if family.director_shot_choices.get("caption_preset") != "hello":
        _fail("saved safe subtitle choice not restored")
        return
    if scene.director_runtime.subtitle_label == null or scene.director_runtime.subtitle_label.text != "Hello, friend!":
        _fail("saved subtitle is missing from restored movie preview")
        return
    if scene.film_note_input.text != "The two heroes celebrate":
        _fail("private story note not restored")
        return
    if scene.director_runtime.actor == null or scene.director_runtime.second_actor == null:
        _fail("reopened film did not stage both canonical actors")
        return
    if scene.director_runtime.duration_seconds != 30.0:
        _fail("reopened film lost 30-second timeline")
        return

    family.disconnect_family()
    if not family.opened_saved_film.is_empty():
        _fail("logout retained another child's saved film")
        return
    print("family_reopen_saved_film_smoke: PASS · server GETs, two outfits, 30s, revisions")
    quit(0)


func _draft() -> Dictionary:
    return {
        "schema_version": "1.0", "display_name": "Cloud Adventure",
        "character_id": "CHAR_OWN_LILY",
        "second_character_id": "CHAR_OWN_CAT",
        "camera": "close", "action": "celebrate",
        "duration_seconds": 30, "caption_preset": "hello",
        "private_story_note": "The two heroes celebrate"
    }


func _record() -> Dictionary:
    return {"schema_version": "1.0", "film_id": FILM_ID,
        "revision": "3", "draft": _draft()}


func _hero(cid: String, tint: String) -> Dictionary:
    return {"schema_version": "1.0", "character_id": cid,
        "display_name": cid, "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "species_head_id": "species_head_cat_v1",
            "surface_color_hex": tint
        }}}


func _gear(cid: String, item: String) -> Dictionary:
    var slot := "weapon_main" if cid == "CHAR_OWN_LILY" else "headwear"
    return {"character_asset_id": cid,
        "equipped": {slot: {
            "item_instance_id": item, "rarity": "gold",
            "display_name": "My Saved Item"
        }},
        "final_stats": {}}


func _fail(message: String) -> void:
    push_error("family_reopen_saved_film_smoke: FAIL " + message)
    quit(1)
