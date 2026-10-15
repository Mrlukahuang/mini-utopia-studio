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
    for action in ["idle", "walk", "run", "jump"]:
        var found := false
        for animation_name in animation_names:
            if String(animation_name).to_lower().contains(action):
                found = true
                break
        if not found:
            _fail("official KayKit Knight.glb missing " + action + " animation")
            return

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


func _inspect_kaykit_actor(node: Node, info: Dictionary) -> void:
    if node is Skeleton3D:
        var skeleton := node as Skeleton3D
        if skeleton.get_bone_count() > int(info.get("bones", 0)):
            info["bones"] = skeleton.get_bone_count()
            info["skeleton"] = String(skeleton.name)
    if node is AnimationPlayer:
        var player := node as AnimationPlayer
        var names: Array = info.get("animations", [])
        for animation_name in player.get_animation_list():
            names.append(String(animation_name))
        info["animations"] = names
    for child in node.get_children():
        _inspect_kaykit_actor(child, info)
