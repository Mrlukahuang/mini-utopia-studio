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
    # Never cover the authentic Knight head with primitive species shells.
    # Unavailable species keep their saved ID, but show the original KayKit rig.
    var old_shell := skeleton.get_node_or_null("KayKitHeadOverlay")
    if old_shell != null:
        skeleton.remove_child(old_shell)
        old_shell.queue_free()
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


