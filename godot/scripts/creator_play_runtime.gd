class_name MiniUtopiaCreatorPlayRuntime
extends Node

const SESSION_PATH := "res://runtime_state/creator_play_session.json"
const EXAMPLE_PATH := "res://config/runtime/creator_play_session_example.json"

var payload: Dictionary = {}
var _player: CharacterBody3D
var _arm_l: Node3D
var _arm_r: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _elapsed := 0.0
var _attack_pose_remaining := 0.0
var _baby: MiniUtopiaBabyFollowRuntime


func apply_to_player(player: CharacterBody3D) -> Dictionary:
    _player = player
    payload = _load_session()
    if payload.is_empty():
        print("PLAY-02: no Creator play-session payload; using scene defaults.")
        return {}

    _ensure_visual_nodes()
    var character: Dictionary = payload.get("character", {})
    _apply_character(character)
    _ensure_runtime_sockets()

    var equipment: Dictionary = payload.get("equipment", {})
    var attached := MiniUtopiaEquipmentRuntime.attach_loadout(
        _player,
        equipment
    )

    var final_stats: Dictionary = equipment.get("final_stats", {})
    _player.set_meta("mini_utopia_stats", final_stats)
    _player.set_meta(
        "mini_utopia_character_asset_id",
        String(payload.get("character_asset_id", ""))
    )
    _player.set_meta(
        "mini_utopia_session_id",
        String(payload.get("session_id", "NO_SESSION"))
    )

    var raw_baby = payload.get("baby", {})
    var baby: Dictionary = (
        raw_baby
        if typeof(raw_baby) == TYPE_DICTIONARY
        else {}
    )
    if not baby.is_empty() and bool(baby.get("active", false)):
        _spawn_baby(baby)

    print(
        "PLAY-02 loaded: ",
        payload.get("character_name", "Mini Traveler"),
        " · slots=",
        ", ".join(attached.keys()),
        " · baby=",
        baby.get("display_name", "—")
    )
    return attached


func update_motion(
    delta: float,
    player_velocity: Vector3,
    on_floor: bool,
    running: bool
) -> void:
    if _arm_l == null or _arm_r == null:
        return

    _elapsed += delta
    _attack_pose_remaining = maxf(
        0.0,
        _attack_pose_remaining - delta
    )
    var horizontal_speed := Vector2(
        player_velocity.x,
        player_velocity.z
    ).length()

    _arm_l.rotation = Vector3.ZERO
    _arm_r.rotation = Vector3.ZERO
    if _leg_l != null:
        _leg_l.rotation = Vector3.ZERO
    if _leg_r != null:
        _leg_r.rotation = Vector3.ZERO

    if _attack_pose_remaining > 0.0:
        _arm_l.rotation.z = 0.18
        _arm_r.rotation.x = -1.12
        _arm_r.rotation.z = -0.72
        return

    if not on_floor:
        _arm_l.rotation.z = 0.62
        _arm_r.rotation.z = -0.62
        return

    if horizontal_speed > 0.15:
        var pace := 8.0 if running else 5.0
        var amount := 0.72 if running else 0.44
        var swing := sin(_elapsed * pace) * amount
        _arm_l.rotation.x = swing
        _arm_r.rotation.x = -swing
        if _leg_l != null:
            _leg_l.rotation.x = -swing * 0.70
        if _leg_r != null:
            _leg_r.rotation.x = swing * 0.70
    else:
        var idle := sin(_elapsed * 1.8) * 0.035
        _arm_l.rotation.z = idle
        _arm_r.rotation.z = -idle


func play_attack_swing() -> void:
    _attack_pose_remaining = 0.22


func _load_session() -> Dictionary:
    var path := SESSION_PATH
    if not FileAccess.file_exists(path):
        path = EXAMPLE_PATH
    return _load_json(path)


func _load_json(path: String) -> Dictionary:
    if not FileAccess.file_exists(path):
        return {}
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _ensure_visual_nodes() -> void:
    var visual := _player.get_node_or_null("Visual") as Node3D
    if visual == null:
        visual = Node3D.new()
        visual.name = "Visual"
        _player.add_child(visual)

    _arm_l = _ensure_box(
        visual,
        "ArmL",
        Vector3(-0.47, 0.90, 0.0),
        Vector3(0.20, 0.62, 0.20),
        Color("#F2C7A5")
    )
    _arm_r = _ensure_box(
        visual,
        "ArmR",
        Vector3(0.47, 0.90, 0.0),
        Vector3(0.20, 0.62, 0.20),
        Color("#F2C7A5")
    )
    _leg_l = _ensure_box(
        visual,
        "LegL",
        Vector3(-0.18, 0.28, 0.0),
        Vector3(0.24, 0.54, 0.26),
        Color("#BFDFF5")
    )
    _leg_r = _ensure_box(
        visual,
        "LegR",
        Vector3(0.18, 0.28, 0.0),
        Vector3(0.24, 0.54, 0.26),
        Color("#BFDFF5")
    )
    _ensure_box(
        visual,
        "FootL",
        Vector3(-0.18, 0.05, 0.08),
        Vector3(0.30, 0.18, 0.40),
        Color("#EEF2FA")
    )
    _ensure_box(
        visual,
        "FootR",
        Vector3(0.18, 0.05, 0.08),
        Vector3(0.30, 0.18, 0.40),
        Color("#EEF2FA")
    )
    _ensure_sphere(
        visual,
        "EyeL",
        Vector3(-0.10, 1.57, 0.31),
        Vector3(0.065, 0.08, 0.05),
        Color("#7A5238")
    )
    _ensure_sphere(
        visual,
        "EyeR",
        Vector3(0.10, 1.57, 0.31),
        Vector3(0.065, 0.08, 0.05),
        Color("#7A5238")
    )


func _apply_character(character: Dictionary) -> void:
    var visual := _player.get_node_or_null("Visual") as Node3D
    if visual == null:
        return

    var body_type := String(character.get("body_type", "standard"))
    var width := MiniUtopiaAvatarContract.body_width_scale(body_type)
    var surface_color := _payload_color(
        character.get("surface_color_hex", "#F2C7A5"),
        Color("#F2C7A5")
    )
    var hair_color := _payload_color(
        character.get("hair_color_hex", "#5B4036"),
        Color("#5B4036")
    )
    var eye_color := _payload_color(
        character.get("eye_color_hex", "#7A5238"),
        Color("#7A5238")
    )

    var body := visual.get_node_or_null("Body") as MeshInstance3D
    if body != null:
        body.scale.x = width
        body.material_override = _material(
            _payload_color(
                character.get("body_color_hex", "#FFF4D7"),
                Color("#FFF4D7")
            )
        )

    var head := visual.get_node_or_null("Head") as MeshInstance3D
    if head != null:
        head.scale.x = 1.0
        head.material_override = _material(surface_color)

    var hair := visual.get_node_or_null("Hair") as MeshInstance3D
    if hair != null:
        hair.visible = String(
            character.get("hair_style_id", "hair_none")
        ) != "hair_none"
        hair.scale.x = 1.06
        hair.material_override = _material(hair_color)

    for eye_name in ["EyeL", "EyeR"]:
        var eye := visual.get_node_or_null(eye_name) as MeshInstance3D
        if eye != null:
            eye.material_override = _material(eye_color)

    if _arm_l != null:
        _arm_l.position.x = -0.47 * width
        _arm_l.material_override = _material(surface_color)
    if _arm_r != null:
        _arm_r.position.x = 0.47 * width
        _arm_r.material_override = _material(surface_color)


func _ensure_runtime_sockets() -> void:
    var sockets := _player.get_node_or_null("Sockets") as Node3D
    if sockets == null:
        sockets = Node3D.new()
        sockets.name = "Sockets"
        _player.add_child(sockets)

    _ensure_socket(
        sockets,
        MiniUtopiaAvatarContract.SOCKET_BACKPACK,
        Vector3(0.0, 0.98, -0.36)
    )
    _ensure_socket(
        sockets,
        MiniUtopiaAvatarContract.SOCKET_WINGS,
        Vector3(0.0, 1.18, -0.38)
    )
    _ensure_socket(
        sockets,
        MiniUtopiaAvatarContract.SOCKET_ACCESSORY,
        Vector3(0.24, 0.96, 0.29)
    )
    _ensure_socket(
        sockets,
        MiniUtopiaAvatarContract.SOCKET_HEADWEAR,
        Vector3(0.0, 1.98, 0.0)
    )

    # Weapon sockets are children of the animated arms. Equipment attached to
    # these sockets therefore follows locomotion/jump motion automatically.
    _ensure_socket(
        _arm_r,
        MiniUtopiaAvatarContract.SOCKET_WEAPON_R,
        Vector3(0.03, -0.31, 0.05)
    )
    _ensure_socket(
        _arm_l,
        MiniUtopiaAvatarContract.SOCKET_WEAPON_L,
        Vector3(-0.03, -0.20, 0.15)
    )


func _spawn_baby(baby: Dictionary) -> void:
    if _baby != null and is_instance_valid(_baby):
        _baby.queue_free()

    _baby = MiniUtopiaBabyFollowRuntime.new()
    var world_parent := _player.get_parent()
    if world_parent == null:
        return
    world_parent.add_child(_baby)
    _baby.global_position = _player.global_position + Vector3(-1.0, 0.2, 0.8)
    _baby.configure(_player, baby)


func _ensure_socket(
    parent: Node3D,
    socket_name: String,
    position: Vector3
) -> Node3D:
    var socket := parent.get_node_or_null(NodePath(socket_name)) as Node3D
    if socket == null:
        socket = Node3D.new()
        socket.name = socket_name
        parent.add_child(socket)
    socket.position = position
    return socket


func _ensure_box(
    parent: Node3D,
    node_name: String,
    position: Vector3,
    size: Vector3,
    color: Color
) -> MeshInstance3D:
    var existing := parent.get_node_or_null(node_name) as MeshInstance3D
    if existing != null:
        return existing

    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = position
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _ensure_sphere(
    parent: Node3D,
    node_name: String,
    position: Vector3,
    scale_value: Vector3,
    color: Color
) -> MeshInstance3D:
    var existing := parent.get_node_or_null(node_name) as MeshInstance3D
    if existing != null:
        return existing

    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = position
    node.scale = scale_value
    var mesh := SphereMesh.new()
    mesh.radius = 0.5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _payload_color(value, fallback: Color) -> Color:
    var text := String(value)
    if text.is_empty():
        return fallback
    return Color(text)


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.82
    return material
