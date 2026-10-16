extends SceneTree

## Child-facing first Hero creation must keep the same canonical AvatarRoot
## and must never enable cloud writes before an adult session is supplied.

func _initialize() -> void:
    # PR3 resources must be genuinely usable in the same CI Web build.
    var kaykit_rig := load("res://assets/kaykit/adventurers/Knight.glb") as PackedScene
    if kaykit_rig == null:
        _fail("official KayKit Knight.glb was not imported")
        return
    var actor := kaykit_rig.instantiate()
    var rig_info := {"bones": 0, "skeleton": "", "animations": []}
    _inspect_kaykit_actor(actor, rig_info)
    actor.free()
    print("Official KayKit Knight rig: ", rig_info)
    if int(rig_info.get("bones", 0)) < 15:
        _fail("official KayKit Knight.glb contains no humanoid Skeleton3D")
        return
    var animation_names: Array = rig_info.get("animations", [])
    # Real source clip names, verified against the Godot-imported official GLB.
    for clip_name in ["Idle", "Walking_A", "Running_A", "Jump_Full_Short"]:
        if not animation_names.has(clip_name):
            _fail("official KayKit Knight.glb missing clip " + clip_name)
            return
    for item_name in ["sword_1handed", "shield_round", "staff", "wand"]:
        var item_path: String = "res://assets/kaykit/adventurers/" + String(item_name) + ".gltf"
        var item_scene := load(item_path) as PackedScene
        if item_scene == null:
            _fail("KayKit equipment failed Godot import: " + item_name)
            return
        var item := item_scene.instantiate()
        if item == null:
            _fail("KayKit equipment could not instantiate: " + item_name)
            return
        item.free()

    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Creator scene missing")
        return
    var scene := packed.instantiate()
    root.add_child(scene)
    await process_frame

    var name_input := scene.get_node(
        "RootMargin/MainColumn/HeaderRow/TitleColumn/HeroNameInput"
    ) as LineEdit
    var save_button := scene.get_node(
        "RootMargin/MainColumn/FooterRow/SaveButton"
    ) as Button
    var play_button := scene.get_node(
        "RootMargin/MainColumn/FooterRow/PlayButton"
    ) as Button
    var stage := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage"
    ) as MiniUtopiaCreatorAvatarStage
    var bridge := scene.get_node("BridgeClient") as MiniUtopiaBridgeClient
    if name_input == null or save_button == null or play_button == null or stage == null:
        _fail("child naming controls missing")
        return

    var avatar_identity := stage.avatar_root_instance_id()
    if stage.avatar_root().get_node_or_null("KayKitBody") == null:
        _fail("Creator screenshot uses fallback instead of real KayKit")
        return
    # A saved legacy nonhuman selection must never cover the official Knight.
    var old_species := stage.current_appearance()
    old_species["species_head_id"] = "species_head_robot_v1"
    stage.apply_appearance(old_species)
    var model := stage.avatar_root().get_node("KayKitBody") as Node3D
    var skeleton := model.find_child("Skeleton3D", true, false) as Skeleton3D
    var identity := skeleton.get_node_or_null("KayKitHeadOverlay") as BoneAttachment3D
    var shell := identity.get_node_or_null("SpeciesShell") as MeshInstance3D if identity != null else null
    if (
        identity == null or identity.visible
        or shell == null or shell.mesh != null
    ):
        _fail("nonhuman legacy identity has a visible species head mesh")
        return
    old_species["species_head_id"] = "species_head_human_v1"
    stage.apply_appearance(old_species)
    var headwear := MiniUtopiaKaykitAvatarV1.mounted_weapon_socket(
        stage.avatar_root(), MiniUtopiaAvatarContract.SOCKET_HEADWEAR
    )
    if (
        headwear == null
        or not (headwear.get_parent() is BoneAttachment3D)
        or (headwear.get_parent() as BoneAttachment3D).bone_name != "head"
        or headwear.visible
    ):
        _fail("headwear is not safely mounted to animated KayKit head bone")
        return
    # First-touch selection has two themed, real SubViewport KayKit cards.
    # Clicking without an adult-issued session cannot expose either child's
    # library or parent-only token inputs.
    # Parent-only widgets must not appear on a child's library screen.
    var library := load("res://scenes/family_hero_library.tscn").instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame
    var chooser := library.get_node_or_null("WhoIsPlaying") as Panel
    var child_a := library.get_node_or_null(
        "WhoIsPlaying/Margin/Column/PlayerCards/PlayerChildA"
    ) as Button
    var child_b := library.get_node_or_null(
        "WhoIsPlaying/Margin/Column/PlayerCards/PlayerChildB"
    ) as Button
    if chooser == null or not chooser.visible:
        _fail("who-is-playing page must be the first Hero Library view")
        return
    # The pastel overlay itself may be translucent, but the underlying
    # library must never bleed through. Closing it restores the same content.
    var library_content := library.get_node_or_null("Margin") as Control
    if library_content == null or library_content.visible:
        _fail("library content shows through who-is-playing chooser")
        return
    chooser.hide()
    if not library_content.visible:
        _fail("library content stays hidden after leaving chooser")
        return
    chooser.show()
    if library_content.visible:
        _fail("library content leaked after reopening chooser")
        return
    if child_a == null or child_b == null:
        _fail("missing two child profile cards")
        return
    for card in [child_a, child_b]:
        if card.custom_minimum_size.y < 300:
            _fail("player card is too small for iPad")
            return
        var avatar := card.get_node_or_null("Portrait3D") as MiniUtopiaCreatorAvatarStage
        if avatar == null or avatar.avatar_root().get_node_or_null("KayKitBody") == null:
            _fail("who-is-playing card needs a real 3D KayKit avatar")
            return
    library._on_player_card_pressed("child_b")
    if not chooser.visible or library.profile_choice.get_selected_id() != 1:
        _fail("unauthorized child switched profiles without adult")
        return
    if library.api_input.visible or library.token_input.visible:
        _fail("child library exposes technical login inputs")
        return
    library._toggle_parent_entry()
    if not library.api_input.visible or not library.token_input.visible:
        _fail("parent entry did not reveal adult login controls")
        return
    library._toggle_parent_entry()
    if library.api_input.visible or library.token_input.visible:
        _fail("parent login controls remained visible on the child page")
        return
    # Parent unlock now uses large on-canvas buttons, not clipboard paste.
    library._open_parent_from_picker()
    var pin_pad := library.get_node_or_null("WhoIsPlaying/ParentPinPad") as Panel
    if pin_pad == null or not pin_pad.visible or library.token_input.visible:
        _fail("the parent eight-digit keypad did not open safely")
        return
    for digit in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        library._press_pin_key(digit)
    if library._parent_pin.length() != 8 or library.parent_pin_submit.disabled:
        _fail("eight-digit parent unlock did not enable the button")
        return
    library._press_pin_key("⌫")
    if not library.parent_pin_submit.disabled:
        _fail("incomplete parent PIN enabled unlock")
        return
    library._close_parent_pin_pad()
    if pin_pad.visible or not chooser.get_node("Margin").visible:
        _fail("parent PIN did not return to the child chooser")
        return
    # Reuse the existing owner-scoped list contract for real 3D cards.
    var family_for_card := root.get_node("FamilySceneState") as MiniUtopiaFamilySceneState
    var synthetic_token := "synthetic_hero_card_token_0123456789abcdef"
    if not family_for_card.connect_family("https://family.example", synthetic_token):
        _fail("synthetic portrait session failed")
        return
    if not family_for_card.bind_family_client(library.bridge):
        _fail("portrait session could not bind")
        return
    library._set_connected(true)
    library._on_bridge_success("characters:list", {
        "schema_version": "1.0",
        "characters": [{
            "character_id": "CHAR_PORTRAIT_TEST",
            "display_name": "Lily",
            "profile": {"avatar": stage.current_appearance()},
        }],
    })
    var portrait_button := library.hero_list.get_node_or_null("Hero_CHAR_PORTRAIT_TEST") as Button
    if portrait_button == null or portrait_button.custom_minimum_size.y < 120:
        _fail("big hero card missing")
        return
    var edit_action := portrait_button.get_node_or_null("HeroActions/EditHero") as Button
    var play_action := portrait_button.get_node_or_null("HeroActions/PlayHero") as Button
    if (
        edit_action == null or play_action == null
        or edit_action.custom_minimum_size.y < 56
        or play_action.custom_minimum_size.y < 56
    ):
        _fail("each saved Hero needs large Edit and Play touch buttons")
        return
    var portrait := portrait_button.get_node_or_null("Portrait3D") as MiniUtopiaCreatorAvatarStage
    if portrait == null or portrait.avatar_root().get_node_or_null("KayKitBody") == null:
        _fail("KayKit 3D SubViewport portrait missing")
        return
    library._on_bridge_success("characters:list", {
        "schema_version": "1.0", "characters": []
    })
    if library.hero_list.get_node_or_null("CreateFirstHeroHint") == null:
        _fail("empty library must show an easy create hint")
        return
    for required_name in ["NewHeroButton", "MyMoviesButton", "BackButton"]:
        var action := library.get_node_or_null("Margin/Column/Toolbar/" + required_name) as Button
        if action == null or action.icon == null or action.custom_minimum_size.y < 60:
            _fail("child library needs three large SVG-icon actions: " + required_name)
            return
    # The chooser still covers the Library after the synthetic list event;
    # close it before inspecting the actual child-facing toolbar.
    chooser.hide()
    if library.refresh_button.is_visible_in_tree() or library.shoot_button.is_visible_in_tree() or library.guests_refresh_button.is_visible_in_tree():
        _fail("adult-only tools leaked into child's library")
        return
    library._toggle_parent_entry()
    if not library.refresh_button.is_visible_in_tree() or library.refresh_button.icon == null:
        _fail("adult refresh must use imported SVG icon")
        return
    library._toggle_parent_entry()
    family_for_card.disconnect_family()
    library.queue_free()

    var name_button := scene.get_node("RootMargin/MainColumn/HeaderRow/HelpNameButton") as Button
    var random_button := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/RandomLookButton"
    ) as Button
    if name_button == null or random_button == null:
        _fail("child-friendly Creator actions missing")
        return
    scene._on_help_name_pressed()
    if not scene.hero_name_input.text.contains(" "):
        _fail("name suggestion should include Chinese and English")
        return
    scene._on_random_look_pressed()
    if not scene._appearance_dirty:
        _fail("random look must be explicitly saved")
        return
    if MiniUtopiaKaykitAvatarV1.hand_skin({
        "compatible_tags": ["humanoid", "kaykit_style_staff"]
    }) != "staff":
        _fail("KayKit hand style not carried with avatar")
        return

    name_input.text = "Lily"
    scene._on_hero_name_changed(name_input.text)
    if not save_button.disabled:
        _fail("unprovisioned browser may not save child data")
        return

    var token := "test_only_family_token_not_a_real_secret_123456"
    if not scene.activate_family_session(token, "https://family.example"):
        _fail("family session activation failed")
        return
    if save_button.disabled:
        _fail("named hero should become saveable with a scoped session")
        return

    name_input.text = ""
    scene._on_hero_name_changed("")
    if not save_button.disabled:
        _fail("empty names should not be saveable")
        return

    name_input.text = "Lily"
    scene._on_hero_name_changed(name_input.text)
    bridge.request_succeeded.emit("character:post", {
        "schema_version": "1.0",
        "character_id": "CHAR_DEMO_LILY",
        "revision": "2026-10-14T00:00:00+00:00",
        "display_name": "Lily",
        "profile": {"avatar": stage.current_appearance()},
    })
    if scene.character_id != "CHAR_DEMO_LILY":
        _fail("created hero did not receive a canonical stable ID")
        return
    var stars := scene.avatar_stage.get_parent().get_node_or_null("SavedStars") as Label
    if stars == null or not stars.visible:
        _fail("save success did not celebrate with visible stars")
        return
    if scene.avatar_stage.current_preview_animation() != "Jump":
        _fail("saved Hero did not jump to celebrate")
        return
    if play_button.text != "🌳 去村子玩！" or play_button.custom_minimum_size.y < 68:
        _fail("save success did not offer the large village button")
        return
    if save_button.disabled:
        _fail("saved hero should remain editable")
        return
    if stage.avatar_root_instance_id() != avatar_identity:
        _fail("saving recreated 3D AvatarRoot")
        return
    if not play_button.disabled:
        _fail("saved Hero could play before its owner-scoped gear loaded")
        return

    # The server response is synthetic; no real child account/secret or
    # network bypass is used. Invalid equipment is never permitted to Play.
    var foreign_runtime := {
        "character_asset_id": "CHAR_OTHER_CHILD",
        "equipped": {}, "final_stats": {}
    }
    bridge.request_succeeded.emit("equipment:get", {"runtime": foreign_runtime})
    if not play_button.disabled:
        _fail("another child's wardrobe enabled Play")
        return
    var owned_runtime := {
        "character_asset_id": "CHAR_DEMO_LILY",
        "equipped": {}, "final_stats": {}
    }
    bridge.request_succeeded.emit("equipment:get", {"runtime": owned_runtime})
    if play_button.disabled:
        _fail("saved Hero and matching gear did not enable Play")
        return

    # Editing an existing Hero must include the new look in the canonical PUT,
    # without changing unrelated profile fields or the server revision.
    scene._draft_appearance["body_type"] = "chubby"
    var updated: Dictionary = scene._character_update_payload("Lily New Look")
    if String(updated.get("display_name", "")) != "Lily New Look":
        _fail("Hero rename was not included in the saved payload")
        return
    if String(updated.get("profile", {}).get("avatar", {}).get("body_type", "")) != "chubby":
        _fail("edited avatar did not persist in the Character PUT payload")
        return
    if String(updated.get("revision", "")) != "2026-10-14T00:00:00+00:00":
        _fail("save dropped the canonical revision")
        return

    # Simulate an optimistic stale-equipment cache after PUT. A successful
    # save must never enable Play for a different child-owned wardrobe.
    scene.equipment_state = {"runtime": foreign_runtime}
    bridge.request_succeeded.emit("character:put", scene.loaded_character)
    if not play_button.disabled:
        _fail("character PUT enabled Play for foreign equipment")
        return
    bridge.request_succeeded.emit("equipment:get", {"runtime": owned_runtime})
    if play_button.disabled:
        _fail("Play did not recover once own equipment was verified")
        return

    # Spawn position is owned by CreatorPlayRuntime, never village.gd.
    var world_stub := Node3D.new()
    world_stub.name = "MiniUtopiaWorld"
    root.add_child(world_stub)
    var dummy := CharacterBody3D.new()
    world_stub.add_child(dummy)
    var runtime := MiniUtopiaCreatorPlayRuntime.new()
    world_stub.add_child(runtime)
    runtime.apply_to_player(dummy)
    if not is_equal_approx(dummy.position.z, 23.0) or not is_equal_approx(dummy.rotation.y, PI):
        _fail("village entrance spawn is incorrect")
        return
    world_stub.queue_free()

    # Press the actual Creator Play handler and verify its two private
    # selections before Godot changes scenes on the following frame.
    scene._on_play_pressed()
    var selection := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if selection == null or String(
        selection.active_character.get("character_id", "")
    ) != "CHAR_DEMO_LILY":
        _fail("Play did not select the server-saved canonical Hero")
        return
    if String(selection.active_equipment.get("character_asset_id", "")) != "CHAR_DEMO_LILY":
        _fail("Play did not select only the saved Hero's own equipment")
        return
    var village_session := selection.active_play_session()
    if String(village_session.get("character_asset_id", "")) != "CHAR_DEMO_LILY":
        _fail("Village did not receive the saved Hero identity")
        return

    print("creator_new_hero_smoke: PASS · parent gate → name → save → owned gear → Play")
    quit(0)


func _fail(message: String) -> void:
    push_error("creator_new_hero_smoke: FAIL · " + message)
    quit(1)


func _inspect_kaykit_actor(node: Node, info: Dictionary) -> void:
    if node is Skeleton3D:
        var skeleton := node as Skeleton3D
        if skeleton.get_bone_count() > int(info.get("bones", 0)):
            info["bones"] = skeleton.get_bone_count()
            info["skeleton"] = String(skeleton.name)
            var bones: Array[String] = []
            for bone_idx in range(skeleton.get_bone_count()):
                bones.append(String(skeleton.get_bone_name(bone_idx)))
            info["bone_names"] = bones
    if node is AnimationPlayer:
        var player := node as AnimationPlayer
        var names: Array = info.get("animations", [])
        for animation_name in player.get_animation_list():
            names.append(String(animation_name))
        info["animations"] = names
    for child in node.get_children():
        _inspect_kaykit_actor(child, info)
