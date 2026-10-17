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


# Dynamic *visual-only* grip pivot. The bundled sword and staff mesh long
# axes are +Y in their GLTF POSITION bounds (sword Y -0.366..1.409,
# staff Y -0.900..1.254); imported handslot_r supplies the true grip.
# Reorient the local +Y long axis in ACTOR SPACE, never toward a moving head.
# This preserves a fixed natural pose through Idle/Walking_A/Running_A.
class HeadClearancePivot extends Node3D:
    var actor: Node3D
    var style := "sword_1handed"

    func _ready() -> void:
        # Imported AnimationPlayer changes handslot_r in idle processing.
        # At default priority 0 the prop can orient before the animated hand,
        # causing one-frame Walk/Run drift toward the helmet. Resolve the
        # visual-only grip AFTER the rig update, with no socket translation.
        process_priority = 100
        _orient_in_actor_space()

    func _process(_delta: float) -> void:
        _orient_in_actor_space()

    func _orient_in_actor_space() -> void:
        if actor == null or get_parent() == null:
            return
        var basis := actor.global_transform.basis.orthonormalized()
        var side := -1.0 if (global_position - actor.global_position).dot(basis.x) < 0.0 else 1.0
        var axis: Vector3
        match style:
            "sword_1handed":
                # Blade 45 degrees above the character's horizontal plane,
                # pointing *forward*, with a small outward bias so it reads
                # clearly in a head-on Creator preview.
                axis = basis.y + basis.z + basis.x * (0.18 * side)
            "staff":
                # A staff is a longer, asymmetrical object. Put the green
                # jewel *outside and behind* the helmet, not in front of the
                # face; the shaft continues to originate at the real grip.
                axis = basis.y * 2.00 - basis.z * 1.45 + basis.x * (1.10 * side)
            _:
                # Short wand: near upright, modest outward tilt.
                axis = basis.y * 1.3 + basis.x * (0.55 * side)
        var local_axis := (
            (get_parent() as Node3D).global_transform.basis.inverse()
            * axis.normalized()
        ).normalized()
        quaternion = Quaternion(Vector3.UP, local_axis)


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
    # Preserve legacy saved identity for cross-scene consumers without rendering
    # any procedural geometry over the official Knight's original head.
    _species_identity_only(skeleton, appearance)
    _hide_native_hand_props(skeleton)
    _bone_socket(skeleton, "handslot.r", MiniUtopiaAvatarContract.SOCKET_WEAPON_R)
    _bone_socket(skeleton, "handslot.l", MiniUtopiaAvatarContract.SOCKET_WEAPON_L)
    # A-012 visual check: no packaged official crown asset exists.
    # CI confirmation: preserve native Knight helmet across every animation.
    # Real headwear belongs to the animated head bone, never a fixed-height
    # world/root socket. No separately licensed KayKit crown model is bundled
    # yet: hide the socket so legacy procedural crowns cannot float over the
    # Knight helmet. Existing saved outfit data stays unchanged.
    _bone_socket(skeleton, "head", MiniUtopiaAvatarContract.SOCKET_HEADWEAR)
    var headwear := skeleton.find_child(
        MiniUtopiaAvatarContract.SOCKET_HEADWEAR, true, false
    ) as Node3D
    if headwear != null:
        headwear.position = Vector3(0.0, 0.24, 0.0)
        headwear.visible = false

    # Keep legacy nodes for the save/preview contract and tests, but never
    # render an overlapping procedural body when official KayKit exists.
    var legacy := root.get_node_or_null("Visual") as Node3D
    if legacy != null:
        for descendant in legacy.find_children("*", "MeshInstance3D", true, false):
            (descendant as MeshInstance3D).visible = false
    return animation


# The bundled Knight GLB has a 1H sword, 2H sword and several shields
# already displayed on its imported hands. They are showcase meshes, NOT
# items owned by the signed-in child. Remove their render layer, even if the
# original animation changes visible, before mounting the verified loadout.
# Do not hide the animated hand bones or the official helmet.
static func _hide_native_hand_props(skeleton: Skeleton3D) -> void:
    for hand in ["handslot_l", "handslot_r"]:
        var original := skeleton.get_node_or_null(hand) as Node3D
        if original == null:
            continue
        # Only original direct mesh children; a runtime Socket_WeaponR/L
        # inserted below the imported holder MUST remain drawable.
        for part in original.get_children():
            if part is MeshInstance3D:
                (part as MeshInstance3D).layers = 0


static func visible_hand_style(root: Node3D, slot: String, style: String) -> bool:
    var socket_name := (
        MiniUtopiaAvatarContract.SOCKET_WEAPON_L
        if slot == "weapon_offhand"
        else MiniUtopiaAvatarContract.SOCKET_WEAPON_R
    )
    var socket := mounted_weapon_socket(root, socket_name)
    if socket == null:
        return false
    var equipment := socket.get_node_or_null("Equipment_" + slot) as Node3D
    if equipment == null or String(equipment.get_meta("kaykit_style", "")) != style:
        return false
    for mesh in equipment.find_children("*", "MeshInstance3D", true, false):
        if (mesh as MeshInstance3D).is_visible_in_tree():
            return true
    return false


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
            if style in ["sword_1handed", "staff", "wand"]:
                var pivot := HeadClearancePivot.new()
                pivot.name = "Equipment_" + slot
                pivot.set_meta("kaykit_style", style)
                pivot.actor = root
                pivot.style = style
                socket.add_child(pivot)
                model.name = "OfficialHandProp"
                pivot.add_child(model)
            else:
                model.name = "Equipment_" + slot
                model.set_meta("kaykit_style", style)
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
    # Prefer the source GLB's already-authored hands: these imported holders
    # have the grip pose/rotation for the bundled KayKit equipment models.
    # A fresh BoneAttachment3D at the bare bone origin turns a long staff into
    # a sideways disc in the real Web screenshot.
    var imported_hand := (
        "handslot_r" if bone_name == "handslot.r" else
        "handslot_l" if bone_name == "handslot.l" else ""
    )
    if not imported_hand.is_empty():
        var existing := skeleton.get_node_or_null(imported_hand) as Node3D
        if existing != null:
            var hand_socket := Node3D.new()
            hand_socket.name = socket_name
            existing.add_child(hand_socket)
            return
    var binding := BoneAttachment3D.new()
    binding.name = "KayKitBone_" + bone_name
    binding.bone_name = bone_name
    skeleton.add_child(binding)
    var socket := Node3D.new()
    socket.name = socket_name
    binding.add_child(socket)



# Compatibility for saved nonhuman IDs: zero meshes, zero drawn species shell.
# The older cross-scene smoke still reads these metadata-only MeshInstance3Ds.
# They MUST remain meshless until official KayKit species assets are supplied.
static func _species_identity_only(skeleton: Skeleton3D, appearance: Dictionary) -> void:
    var previous := skeleton.get_node_or_null("KayKitHeadOverlay")
    if previous != null:
        skeleton.remove_child(previous)
        previous.free()
    if String(appearance.get("species_head_id", "species_head_human_v1")) == "species_head_human_v1":
        return
    if skeleton.find_bone("head") < 0:
        return

    var anchor := BoneAttachment3D.new()
    anchor.name = "KayKitHeadOverlay"
    anchor.bone_name = "head"
    anchor.visible = false
    skeleton.add_child(anchor)
    var identity_shell := MeshInstance3D.new()
    identity_shell.name = "SpeciesShell"
    # Mesh intentionally null: never cover the true KayKit head.
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(String(appearance.get("surface_color_hex", "#F2C7A5")))
    identity_shell.material_override = material
    anchor.add_child(identity_shell)
    for node_name in ["SpeciesEarL", "SpeciesEarR"]:
        var ear_identity := MeshInstance3D.new()
        ear_identity.name = node_name
        anchor.add_child(ear_identity)
