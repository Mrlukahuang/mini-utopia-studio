extends SceneTree

## Child-facing first Hero creation must keep the same canonical AvatarRoot
## and must never enable cloud writes before an adult session is supplied.

func _initialize() -> void:
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
    var stage := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage"
    ) as MiniUtopiaCreatorAvatarStage
    var bridge := scene.get_node("BridgeClient") as MiniUtopiaBridgeClient
    if name_input == null or save_button == null or stage == null:
        _fail("child naming controls missing")
        return

    var avatar_identity := stage.avatar_root_instance_id()
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
    if save_button.disabled:
        _fail("saved hero should remain editable")
        return
    if stage.avatar_root_instance_id() != avatar_identity:
        _fail("saving recreated 3D AvatarRoot")
        return

    print("creator_new_hero_smoke: PASS · name, private auth, canonical ID")
    quit(0)


func _fail(message: String) -> void:
    push_error("creator_new_hero_smoke: FAIL · " + message)
    quit(1)
