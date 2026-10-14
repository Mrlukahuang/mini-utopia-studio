extends SceneTree

## Simulate two canonical Character/Equipment responses that the API returns
## to ONE authenticated child session. No real child data or network required.

const TOKEN := "synthetic_cast_test_child_scope_0123456789abcdefghijkl"

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        _fail("FamilySceneState not registered")
        return
    family.disconnect_family()
    if not family.connect_family("https://family.example", TOKEN):
        _fail("test session invalid")
        return

    var lily := _contract("CHAR_MY_LILY", "#F7B7D2")
    var cat := _contract("CHAR_MY_CAT", "#B9E7D0")
    if not family.select_character(lily):
        _fail("main Character could not be selected")
        return
    if not family.select_equipment(_equipment("CHAR_MY_LILY", "ITEM_LILY_HAT")):
        _fail("main Character Equipment rejected")
        return

    var packed := load("res://scenes/family_hero_library.tscn") as PackedScene
    if packed == null:
        _fail("My Heroes scene missing")
        return
    var library := packed.instantiate() as MiniUtopiaFamilyHeroLibrary
    # Disconnect temporarily before adding scene to avoid any background
    # live request. Then restore the in-memory test fixture.
    family.disconnect_family()
    root.add_child(library)
    await process_frame
    if not family.connect_family("https://family.example", TOKEN):
        _fail("scoped session lost")
        return
    family.select_character(lily)
    family.select_equipment(_equipment("CHAR_MY_LILY", "ITEM_LILY_HAT"))
    if not family.bind_family_client(library.bridge):
        _fail("library did not accept current child session")
        return
    library._set_connected(true)
    library._on_bridge_success("characters:list", {
        "schema_version": "1.0",
        "characters": [lily, cat]
    })
    await process_frame

    var same := library.hero_list.get_node_or_null("Cast_CHAR_MY_LILY")
    var cast := library.hero_list.get_node_or_null("Cast_CHAR_MY_CAT") as Button
    if same != null or cast == null:
        _fail("film partner picker should offer only another saved Hero")
        return
    if cast.custom_minimum_size.y < 48:
        _fail("cast button is too small for child on iPad")
        return
    if cast.pressed.get_connections().is_empty():
        _fail("second Hero cast button is not connected")
        return
    if not library.shoot_button.disabled:
        _fail("Film Together must stay disabled before verified Equipment")
        return

    # Simulate server-scoped GET /characters/{CHAR_MY_CAT}. The state contract
    # still rejects the primary's ID and cannot accept unverified equipment.
    library._pending_cast_character_id = "CHAR_MY_CAT"
    if not family.select_second_cast_character(cat):
        _fail("server-returned second character rejected")
        return
    library._on_bridge_success("equipment:get", {
        "character_id": "CHAR_MY_CAT",
        "runtime": _equipment("CHAR_MY_LILY", "ITEM_WRONG_OWNER"),
        "slots": [], "items": []
    })
    if not library.shoot_button.disabled:
        _fail("mismatched Equipment illegally enabled film")
        return
    if not family.second_cast_play_session().is_empty():
        _fail("rejected wardrobe leaked into cast")
        return

    family.select_second_cast_character(cat)
    library._pending_cast_character_id = "CHAR_MY_CAT"
    library._on_bridge_success("equipment:get", {
        "character_id": "CHAR_MY_CAT",
        "runtime": _equipment("CHAR_MY_CAT", "ITEM_CAT_HAT"),
        "slots": [], "items": []
    })
    if library.shoot_button.disabled:
        _fail("verified second actor not film-ready")
        return
    var staged := MiniUtopiaFamilyDirectorSession.from_two_play_sessions(
        family.active_play_session(), family.second_cast_play_session()
    )
    if staged.is_empty() or staged.get("second_character_asset_id") != "CHAR_MY_CAT":
        _fail("film session lost second Hero stable ID")
        return
    if staged.get("second_play_session", {}).get("equipment", {}).get(
        "equipped", {}
    ).get("headwear", {}).get("item_instance_id") != "ITEM_CAT_HAT":
        _fail("second Hero wardrobe lost on Director handoff")
        return

    # Switching profiles disconnects and clears both Characters/equipment.
    library._on_disconnect_pressed()
    if not family.active_character.is_empty():
        _fail("logout leaked first Hero")
        return
    if not family.second_cast_play_session().is_empty():
        _fail("logout leaked second Hero")
        return
    if not library.shoot_button.disabled:
        _fail("Film Together remained enabled after logout")
        return

    print("family_cast_picker_smoke: PASS · same owner, second outfit, no leaks")
    quit(0)


func _contract(cid: String, color: String) -> Dictionary:
    return {
        "schema_version": "1.0",
        "character_id": cid,
        "display_name": cid,
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "species_head_id": "species_head_cat_v1",
            "surface_color_hex": color,
        }},
    }


func _equipment(cid: String, item: String) -> Dictionary:
    return {
        "character_asset_id": cid,
        "equipped": {"headwear": {
            "item_instance_id": item, "display_name": "Small Crown",
            "rarity": "purple",
        }},
        "final_stats": {},
    }


func _fail(message: String) -> void:
    push_error("family_cast_picker_smoke: FAIL · " + message)
    quit(1)
