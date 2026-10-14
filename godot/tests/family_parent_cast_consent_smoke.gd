extends SceneTree

## Family actor sharing is parent-approved on the server. These UI fixtures
## contain only synthetic data; no external requests, real credentials/media.

const CHILD_TOKEN := "synthetic_only_owner_cast_session_0123456789abcdef"

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        _fail("FamilySceneState missing")
        return
    family.disconnect_family()
    var packed := load("res://scenes/family_hero_library.tscn") as PackedScene
    if packed == null:
        _fail("My Heroes scene missing")
        return
    var library := packed.instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame

    if not family.connect_family("https://family.example", CHILD_TOKEN, "child_b"):
        _fail("private child B profile session missing")
        return
    if not family.bind_family_client(library.bridge):
        _fail("child session not bound")
        return
    library._set_connected(true)
    var cat := _hero("CHAR_TEST_B_CAT", "#B9E7D0")
    library._on_bridge_success("characters:list", {
        "schema_version": "1.0", "characters": [cat]
    })
    await process_frame
    var share := library.hero_list.get_node_or_null(
        "Share_CHAR_TEST_B_CAT"
    ) as Button
    if share == null or share.pressed.get_connections().is_empty():
        _fail("parent's share actor control missing")
        return
    library._on_share_candidate("CHAR_TEST_B_CAT")
    if not library.adult_share_panel.visible:
        _fail("explicit parent approval panel not displayed")
        return
    if not library.share_secret_input.secret:
        _fail("parent secret entry must be masked")
        return
    if library.share_submit.pressed.get_connections().is_empty():
        _fail("approve action is not wired")
        return

    library._on_bridge_success("family:cast-approve", {
        "schema_version": "1.0",
        "grant_id": "CAST_TEST_ADULT_APPROVED_0123456789abcdef",
        "viewer_profile_id": "child_a",
        "source_profile_id": "child_b",
        "character_id": "CHAR_TEST_B_CAT",
        "expires_in_seconds": 900
    })
    if not library.share_revoke.visible:
        _fail("parent cannot revoke issued consent")
        return
    if library.share_revoke.pressed.get_connections().is_empty():
        _fail("revoke action not connected")
        return

    # Switch to child A: cannot keep child B's main Hero.
    family.disconnect_family()
    library.bridge.clear_family_session()
    library._set_connected(false)
    if family.has_family_connection():
        _fail("disconnect retained child B token")
        return
    if not family.connect_family("https://family.example", CHILD_TOKEN, "child_a"):
        _fail("private child A profile session missing")
        return
    var sheep := _hero("CHAR_TEST_A_SHEEP", "#F7B7D2")
    if not family.select_character(sheep):
        _fail("child A's main Hero missing")
        return
    if not family.select_equipment({
        "character_asset_id": "CHAR_TEST_A_SHEEP",
        "equipped": {}, "final_stats": {}
    }):
        _fail("child A's owned wardrobe missing")
        return
    if not family.bind_family_client(library.bridge):
        _fail("child A scope not bound")
        return
    library._set_connected(true)
    library._on_bridge_success("castguests:list", {
        "schema_version": "1.0",
        "guests": [{
            "grant_id": "CAST_TEST_ADULT_APPROVED_0123456789abcdef",
            "character_id": "CHAR_TEST_B_CAT",
            "display_name": "Sibling's Cat",
            "expires_in_seconds": 900
        }]
    })
    await process_frame
    var guest := library.hero_list.get_node_or_null(
        "Guest_CAST_TEST_ADULT_APPROVED_0123456789abcdef"
    ) as Button
    if guest == null or guest.custom_minimum_size.y < 48:
        _fail("approved guest not visible to recipient child on iPad")
        return
    if guest.pressed.get_connections().is_empty():
        _fail("guest choice is not wired")
        return
    if not library.shoot_button.disabled:
        _fail("Film Together enabled before guest snapshot verification")
        return

    library._pending_guest_grant_id = "CAST_TEST_ADULT_APPROVED_0123456789abcdef"
    library._on_bridge_success("castguests:get", {
        "schema_version": "1.0",
        "grant_id": "CAST_TEST_ADULT_APPROVED_0123456789abcdef",
        "character": cat,
        "equipment_runtime": {
            "character_asset_id": "CHAR_TEST_B_CAT",
            "equipped": {"headwear": {
                "item_instance_id": "ITEM_TEST_B_CROWN",
                "rarity": "gold", "display_name": "Cat Crown"
            }},
            "final_stats": {}
        }
    })
    if library.shoot_button.disabled:
        _fail("server-approved guest could not join movie")
        return
    var movie := MiniUtopiaFamilyDirectorSession.from_two_play_sessions(
        family.active_play_session(), family.second_cast_play_session()
    )
    if movie.is_empty():
        _fail("parent-approved guest not reusable by shared two-actor Director")
        return
    if movie.get("second_character_asset_id") != "CHAR_TEST_B_CAT":
        _fail("guest stable Character ID changed")
        return
    library._pending_guest_grant_id = "CAST_TEST_ADULT_APPROVED_0123456789abcdef"
    library._on_bridge_failure("castguests:get", 404, "not_found", "")
    if not library.shoot_button.disabled:
        _fail("expired/revoked guest remained eligible for filming")
        return

    family.disconnect_family()
    print("family_parent_cast_consent_smoke: PASS · parent share, child guest, revoke")
    quit(0)


func _hero(cid: String, tint: String) -> Dictionary:
    return {
        "schema_version": "1.0", "character_id": cid, "display_name": cid,
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "species_head_id": "species_head_cat_v1",
            "surface_color_hex": tint
        }}
    }


func _fail(message: String) -> void:
    push_error("family_parent_cast_consent_smoke: FAIL · " + message)
    quit(1)
