class_name MiniUtopiaKaykitAvatarV1
extends RefCounted

## One original KayKit rig/appearance adapter for Creator, Village and Director.
## The same canonical saved AvatarAppearance is passed to all three callers.
const KNIGHT := "res://assets/kaykit/adventurers/Knight.glb"
const CLIPS := {"Idle": "Idle", "Walk": "Walking_A", "Run": "Running_A", "Jump": "Jump_Full_Short"}
const WEAPONS := {
    "sword_1handed": "res://assets/kaykit/adventurers/sword_1handed.gltf",
    "shield_round": "res://assets/kaykit/adventurers/shield_round.gltf",
    "staff": "res://assets/kaykit/adventurers/staff.gltf",
    "wand": "res://assets/kaykit/adventurers/wand.gltf",
}


static func mount(root: Node3D, appearance: Dictionary) -> AnimationPlayer:
    var model := root.get_node_or_null("KayKitBody") as Node3D
    if model == null:
        var scene := load(KNIGHT) as PackedScene
        if scene == null:
            return null  # Real missing resource: preserve original placeholder.
        model = scene.instantiate() as Node3D
        if model == null:
            return null
        model.name = "KayKitBody"
        root.add_child(model)

    var skeleton := model.find_child("Skeleton3D", true, false) as Skeleton3D
    var animation := model.find_child("AnimationPlayer", true, false) as AnimationPlayer
    if skeleton == null or animation == null:
        model.visible = false
        return null

    var width := MiniUtopiaAvatarContract.body_width_scale(
        String(appearance.get("body_type", "standard"))
    )
    model.scale = Vector3(width, 1.0, width)
    model.visible = true
    _head_for_species(skeleton, appearance)
    _bone_socket(skeleton, "handslot.r", MiniUtopiaAvatarContract.SOCKET_WEAPON_R)
    _bone_socket(skeleton, "handslot.l", MiniUtopiaAvatarContract.SOCKET_WEAPON_L)

    # Keep legacy nodes for the save/preview contract and tests, but never
    # render an overlapping procedural body when official KayKit exists.
    var legacy := root.get_node_or_null("Visual") as Node3D
    if legacy != null:
        for descendant in legacy.find_children("*", "MeshInstance3D", true, false):
            (descendant as MeshInstance3D).visible = false
    return animation


static func hand_skin(appearance: Dictionary) -> String:
    var tags = appearance.get("compatible_tags", [])
    if typeof(tags) != TYPE_ARRAY:
        return ""
    for tag in tags:
        var value := String(tag).trim_prefix("kaykit_style_")
        if WEAPONS.has(value):
            return value
    return ""


static func apply_hand_skin(root: Node3D, appearance: Dictionary, equipment: Dictionary) -> void:
    var style := hand_skin(appearance)
    if style.is_empty():
        return
    var equipped = equipment.get("equipped", {})
    if typeof(equipped) != TYPE_DICTIONARY:
        return
    var slot := "weapon_offhand" if style == "shield_round" else "weapon_main"
    if not equipped.has(slot):
        return
    var owned_item = equipped.get(slot, {})
    if typeof(owned_item) != TYPE_DICTIONARY:
        return
    var crafted = owned_item.get("visual_recipe", {})
    if typeof(crafted) == TYPE_DICTIONARY and not crafted.is_empty():
        return
    var socket_name := (
        MiniUtopiaAvatarContract.SOCKET_WEAPON_L
        if slot == "weapon_offhand"
        else MiniUtopiaAvatarContract.SOCKET_WEAPON_R
    )
    var socket := mounted_weapon_socket(root, socket_name)
    if socket == null:
        return
    var previous := socket.get_node_or_null("Equipment_" + slot)
    if previous != null:
        socket.remove_child(previous)
        previous.free()
    var packed := load(String(WEAPONS[style])) as PackedScene
    if packed != null:
        var model := packed.instantiate() as Node3D
        if model != null:
            model.name = "Equipment_" + slot
            socket.add_child(model)


static func play(animation: AnimationPlayer, semantic: String) -> void:
    if animation == null:
        return
    var clip := String(CLIPS.get(semantic, CLIPS["Idle"]))
    if animation.has_animation(clip) and animation.current_animation != clip:
        animation.play(clip)


static func mounted_weapon_socket(root: Node3D, socket_name: String) -> Node3D:
    var model := root.get_node_or_null("KayKitBody") as Node3D
    if model == null or not model.visible:
        return null
    return model.find_child(socket_name, true, false) as Node3D


static func _bone_socket(
    skeleton: Skeleton3D, bone_name: String, socket_name: String
) -> void:
    if skeleton.find_bone(bone_name) < 0:
        return
    if skeleton.find_child(socket_name, true, false) != null:
        return
    var binding := BoneAttachment3D.new()
    binding.name = "KayKitBone_" + bone_name
    binding.bone_name = bone_name
    skeleton.add_child(binding)
    var socket := Node3D.new()
    socket.name = socket_name
    binding.add_child(socket)


static func _head_for_species(skeleton: Skeleton3D, appearance: Dictionary) -> void:
    var previous := skeleton.get_node_or_null("KayKitHeadOverlay")
    if previous != null:
        skeleton.remove_child(previous)
        previous.free()
    var species := String(appearance.get("species_head_id", "species_head_human_v1"))
    if species == "species_head_human_v1" or skeleton.find_bone("head") < 0:
        return

    # All four nonhuman Creator choices remain real, visually distinct heads
    # mounted to the *animated* original KayKit head bone in every runtime.
    var anchor := BoneAttachment3D.new()
    anchor.name = "KayKitHeadOverlay"
    anchor.bone_name = "head"
    skeleton.add_child(anchor)
    var color := Color(String(appearance.get("surface_color_hex", "#F2C7A5")))
    var eye_color := Color(String(appearance.get("eye_color_hex", "#7A5238")))
    var head := MeshInstance3D.new()
    head.name = "SpeciesShell"
    if species == "species_head_robot_v1":
        var cube := BoxMesh.new()
        cube.size = Vector3(0.72, 0.64, 0.70)
        head.mesh = cube
    else:
        var sphere := SphereMesh.new()
        sphere.radius = 0.48 if species == "species_head_cloud_v1" else 0.42
        sphere.height = 0.90 if species == "species_head_cloud_v1" else 0.79
        head.mesh = sphere
    head.material_override = _material(color)
    head.position = Vector3(0, 0.06, 0.0)
    anchor.add_child(head)

    for side in [-1.0, 1.0]:
        var eye := MeshInstance3D.new()
        eye.name = "SpeciesEyeL" if side < 0.0 else "SpeciesEyeR"
        var eye_mesh := SphereMesh.new()
        eye_mesh.radius = 0.072
        eye_mesh.height = 0.14
        eye.mesh = eye_mesh
        eye.material_override = _material(eye_color)
        eye.position = Vector3(side * 0.17, 0.11, 0.40)
        anchor.add_child(eye)
        if species in ["species_head_cat_v1", "species_head_sheep_v1"]:
            var ear := MeshInstance3D.new()
            ear.name = "SpeciesEarL" if side < 0.0 else "SpeciesEarR"
            var ear_mesh := SphereMesh.new()
            ear_mesh.radius = 0.15
            ear_mesh.height = 0.39 if species == "species_head_cat_v1" else 0.22
            ear.mesh = ear_mesh
            ear.material_override = _material(color)
            ear.position = Vector3(side * 0.36, 0.35, 0.0)
            anchor.add_child(ear)


static func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.85
    return material
