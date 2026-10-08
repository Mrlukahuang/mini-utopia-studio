extends SceneTree


func _initialize() -> void:
    var avatar := _build_avatar()
    root.add_child(avatar)

    var first := {
        "equipped": {
            "top": {
                "display_name": "Explorer Top",
                "rarity": "green",
            },
            "bottom": {
                "display_name": "Adventure Pants",
                "rarity": "blue",
            },
            "shoes": {
                "display_name": "Cloud Sneakers",
                "rarity": "purple",
            },
            "weapon_main": {
                "display_name": "Starwood Sword",
                "rarity": "purple",
            },
        }
    }
    var attached := MiniUtopiaEquipmentRuntime.attach_loadout(
        avatar,
        first
    )
    if not attached.has("weapon_main"):
        _fail("main-hand equipment did not attach")
        return

    var socket := avatar.find_child(
        MiniUtopiaAvatarContract.SOCKET_WEAPON_R,
        true,
        false
    ) as Node3D
    if socket == null or socket.get_child_count() != 1:
        _fail("main-hand socket did not contain one equipment visual")
        return

    var body := avatar.get_node("Visual/Body") as MeshInstance3D
    var foot := avatar.get_node("Visual/FootL") as MeshInstance3D
    var base_body_material: Variant = body.get_meta(
        "mini_utopia_base_material",
        null
    )
    var base_foot_material: Variant = foot.get_meta(
        "mini_utopia_base_material",
        null
    )
    if base_body_material == null or base_foot_material == null:
        _fail("clothing base materials were not remembered")
        return

    MiniUtopiaEquipmentRuntime.attach_loadout(
        avatar,
        {"equipped": {}}
    )

    if socket.get_child_count() != 0:
        _fail("unequipped main-hand visual stayed on socket")
        return
    if body.material_override.albedo_color != (
        base_body_material as StandardMaterial3D
    ).albedo_color:
        _fail("Top visual did not restore base body material")
        return
    if foot.material_override.albedo_color != (
        base_foot_material as StandardMaterial3D
    ).albedo_color:
        _fail("Shoes visual did not restore base foot material")
        return

    print(
        "equipment_runtime_sync_smoke: PASS · "
        + "complete loadout removes stale socket and clothing visuals"
    )
    quit(0)


func _build_avatar() -> Node3D:
    var avatar := Node3D.new()
    avatar.name = "AvatarRoot"

    var visual := Node3D.new()
    visual.name = "Visual"
    avatar.add_child(visual)

    _add_box(visual, "Body", Color("#D7C2F3"))
    _add_box(visual, "LegL", Color("#BDE3F5"))
    _add_box(visual, "LegR", Color("#BDE3F5"))
    _add_box(visual, "FootL", Color("#F6F1E8"))
    _add_box(visual, "FootR", Color("#F6F1E8"))

    var sockets := Node3D.new()
    sockets.name = "Sockets"
    avatar.add_child(sockets)
    MiniUtopiaAvatarContract.ensure_socket_nodes(sockets)
    return avatar


func _add_box(parent: Node3D, name_value: String, color: Color) -> void:
    var node := MeshInstance3D.new()
    node.name = name_value
    var mesh := BoxMesh.new()
    mesh.size = Vector3.ONE
    node.mesh = mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    node.material_override = material
    parent.add_child(node)


func _fail(message: String) -> void:
    push_error("equipment_runtime_sync_smoke: FAIL · %s" % message)
    quit(1)
