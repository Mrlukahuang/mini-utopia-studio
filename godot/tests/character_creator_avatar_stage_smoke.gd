extends SceneTree


func _initialize() -> void:
    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Character Creator scene is missing")
        return

    var scene := packed.instantiate()
    root.add_child(scene)
    await process_frame

    var stage := scene.get_node_or_null(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage"
    ) as MiniUtopiaCreatorAvatarStage
    if stage == null:
        _fail("persistent AvatarStage missing")
        return

    var first_id := stage.avatar_root_instance_id()
    if first_id == 0:
        _fail("AvatarRoot was not created")
        return

    var slim := {
        "rig_family": "humanoid_kaykit_v1",
        "body_type": "slim",
        "species_head_id": "species_head_cat_v1",
        "surface_type": "fur",
        "surface_color_hex": "#F7B7D2",
        "eye_style_id": "eyes_cat_v1",
        "eye_color_hex": "#BDE3F5",
        "hair_style_id": "hair_ponytail_v1",
        "hair_color_hex": "#5B4036",
    }
    stage.apply_appearance(slim)

    var root_node := stage.avatar_root()
    var body := root_node.get_node("Visual/Body") as MeshInstance3D
    var slim_width := body.scale.x
    if abs(slim_width - 0.84) > 0.001:
        _fail("Slim body width did not use Avatar contract")
        return

    var chubby := slim.duplicate(true)
    chubby["body_type"] = "chubby"
    chubby["hair_style_id"] = "hair_bob_v1"
    stage.apply_appearance(chubby)

    if stage.avatar_root_instance_id() != first_id:
        _fail("AvatarRoot was recreated instead of mutated")
        return

    var chubby_width := body.scale.x
    if abs(chubby_width - 1.16) > 0.001:
        _fail("Chubby body width did not use Avatar contract")
        return

    var current := stage.current_appearance()
    if current.get("hair_style_id") != "hair_bob_v1":
        _fail("canonical Hair state was not applied")
        return

    var sockets := root_node.get_node_or_null("Sockets")
    if sockets == null:
        _fail("Avatar socket root missing")
        return
    for socket_name in MiniUtopiaAvatarContract.SOCKET_NAMES:
        if sockets.get_node_or_null(socket_name) == null:
            _fail("missing canonical socket: %s" % socket_name)
            return

    print(
        "character_creator_avatar_stage_smoke: PASS · "
        + "AvatarRoot persisted across canonical appearance updates"
    )
    quit(0)


func _fail(message: String) -> void:
    push_error("character_creator_avatar_stage_smoke: FAIL · %s" % message)
    quit(1)
